"""Opt-in public-document policy; never cleans or rewrites an existing release."""

from __future__ import annotations

import re
import stat
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from .deliverables import DeliverableNames, validate_edition

PUBLIC_MODE = "public-documents-only"
PUBLIC_COVER = "公開文書: 参加者ガイド Word 1 点と同じ版の HTML 1 点"
PUBLIC_NOTICE = (
    "公開文書は、参加者ガイド Word 1 点と同じ版の HTML 1 点です。"
    "検証記録票 Word と処理仕様 XLSX は任意の内部補助資料であり、公開セットには含めません。"
    "評価基準と記録方法は第 17 章、全パラメーターの仕様表への索引は付録 B にあります。"
    "実習用 Notebook・コード・データはこの文書ペアには同梱しません。実習前に別途提供方法を確認してください。"
)
PUBLIC_RECORD_INTRO = (
    "Data Agent の評価は、10 問の口語・敵対的な質問で行います。"
    "すべて 1 問 1 会話（fresh conversation）で実施し、質問文をそのまま貼り付けます。"
    "答えは事前に Agent へ教えません。公開版では本章の評価基準と次の記録方法を使用します。"
)
PUBLIC_RECORD_NOTE = (
    "別冊のダウンロードは不要です。ご自身の非公開の記録に、実施日時・実施者・対象 Workspace / Folder・"
    "Data Agent の実 ID・構成版・runtime・Draft / Published・Core / Optional・追加ツール・"
    "未実施 / ブロックの理由を残します。各問の ID と質問原文、実際の回答、使用ソース、安定 ID、数値、"
    "粒度・期間・境界・拒否理由、実行詳細の参照先、判定と所見を記録し、4 判定の件数を集計します。"
    "Core の判定と任意の比較は別に記録します。修正内容・再実施日時・再実行回数・残課題も残します。"
    "回答原本は保持し、公開用の画面写真だけでアカウント・URL・内部 ID を切り抜きまたは伏せ字にして、"
    "加工範囲を明記します。回答を編集して PASS に変えてはいけません。"
    "質問・期待値・実行結果を Agent の設定へ転記しません。"
)
PUBLIC_PARAMETER_NOTE = (
    "全パラメーターの完全な仕様表は、この付録の索引が示す第 6.4 節・第 15.2 節・付録 D.1〜D.3 にあります。"
    "このガイドだけで既定値・変更条件・安全ゲートを確認できます。"
    "処理仕様ワークブックは任意の内部補助資料であり、公開版の実施に XLSX のダウンロードは不要です。"
)


class PublicationError(ValueError):
    """An unsafe path, incomplete pair, or misleading public-document claim."""


def display_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)


def safe_path(path: Path) -> Path:
    """Reject traversal and links before resolution (including Windows junctions)."""
    path = Path(path)
    if str(path).startswith(("\\\\?\\", "\\\\.\\")):
        raise PublicationError(f"Windows device/extended namespaces are not allowed: {path}")
    if ".." in path.parts:
        raise PublicationError(f"parent traversal is not allowed: {path}")
    if path.drive and not path.root:
        raise PublicationError(f"drive-relative paths are not allowed: {path}")
    for component in path.parts:
        if component == path.anchor:
            continue
        if (
            ":" in component or component.rstrip(". ") != component
            or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", component)
        ):
            raise PublicationError(f"ambiguous or reserved Windows path component: {component!r}")
    absolute = path.absolute()
    for part in (*reversed(absolute.parents), absolute):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise PublicationError(f"symbolic links and reparse points are not allowed: {part}")
    return absolute.resolve()


def outside_repo(path: Path, root: Path) -> Path:
    path = safe_path(path)
    if path.is_relative_to(root.resolve()):
        raise PublicationError("public staging/export and its manifest must be outside the repository")
    return path


def public_names_checked(names: DeliverableNames) -> None:
    for name in names.public_pair:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name != Path(name).name:
            raise PublicationError(f"unsafe public filename: {name!r}")


def require_public_edition(edition: str) -> None:
    if not validate_edition(edition):
        raise PublicationError("--public-documents-only requires a nonempty --edition")


def check_directory(
    directory: Path, names: DeliverableNames, *, required: tuple[str, ...] = ()
) -> Path:
    """Allow only selected regular files; fail on extras rather than deleting them."""
    public_names_checked(names)
    directory = safe_path(directory)
    if directory.exists() and not directory.is_dir():
        raise PublicationError(f"not a directory: {directory}")
    entries = {entry.name: entry for entry in directory.iterdir()} if directory.exists() else {}
    unexpected = set(entries) - set(names.public_pair)
    if unexpected:
        raise PublicationError(f"unexpected files in {directory}: {sorted(unexpected)}")
    for entry in entries.values():
        safe_path(entry)
        info = entry.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PublicationError(f"expected an unlinked regular file: {entry}")
    missing = set(required) - set(entries)
    if missing:
        raise PublicationError(f"missing public documents in {directory}: {sorted(missing)}")
    return directory


def prepare_public_build(
    root: Path, directory: Path, names: DeliverableNames, edition: str, *, html: bool = False
) -> Path:
    require_public_edition(edition)
    directory = outside_repo(directory, root)
    check_directory(directory, names, required=(names.participant,) if html else ())
    target = directory / (names.html if html else names.participant)
    if target.exists() or (not html and directory.exists() and any(directory.iterdir())):
        raise PublicationError(f"refusing to overwrite a build; choose a fresh staging directory: {directory}")
    return directory


def public_link_error(value: str, names: DeliverableNames) -> str | None:
    """Only the selected Word download, anchors and ordinary web references are links."""
    if value == names.participant or value.startswith("#"):
        return None
    try:
        decoded = unquote(value).replace("\\", "/")
        link = urlsplit(decoded)
    except ValueError:
        return f"invalid public link: {value!r}"
    if re.search(r"\.(?:docx?|xlsx?|zip)(?:$|[/?#])", decoded, re.IGNORECASE):
        return f"excluded companion or archive link: {value!r}"
    if link.scheme not in {"https", "http"} or not link.netloc:
        return f"unpackaged or unsafe local link: {value!r}"
    return None


def public_text_errors(text: str) -> list[str]:
    plain = text.replace("`", "")
    errors = [
        f"missing public guidance: {label}"
        for label, value in (
            ("document scope", PUBLIC_NOTICE),
            ("in-guide record instructions", PUBLIC_RECORD_NOTE),
            ("in-guide parameter specifications", PUBLIC_PARAMETER_NOTE),
        )
        if value.replace("`", "") not in plain
    ]
    for stale in (
        "記録は別冊の Test 10 記録票を使用します",
        "このガイドと同じ配布版の処理仕様ワークブック",
    ):
        if stale in plain:
            errors.append(f"mandatory nonpublic companion wording: {stale}")
    return errors


_WORD_NAMESPACES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}
_ATTACHMENT_RELATIONSHIPS = {"package", "oleobject", "subdocument", "afchunk", "control", "activexcontrolbinary"}
_OFFICE_CONTENT_PREFIXES = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.",
    "application/vnd.openxmlformats-officedocument.presentationml.",
    "application/vnd.ms-word.",
    "application/vnd.ms-excel.",
    "application/vnd.ms-powerpoint.",
)
_MAIN_WORD_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
_ATTACHMENT_CONTENT_TYPES = {
    "application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.package",
    "application/vnd.ms-office.vbaproject", "application/vnd.ms-office.activex+xml",
    "application/vnd.ms-office.activex", "application/x-ole-storage", "application/x-cfb",
    "application/zip", "application/x-zip-compressed",
    "application/pdf", "application/rtf", "text/rtf", "text/html", "application/xhtml+xml",
    "message/rfc822",
}


def _attachment_content_type(content_type: str, part: str | None) -> bool:
    if content_type in _ATTACHMENT_CONTENT_TYPES or content_type.endswith(".oleobject"):
        return True
    if content_type.startswith(_OFFICE_CONTENT_PREFIXES):
        if not content_type.endswith("+xml"):
            return True
        if content_type.endswith(".main+xml"):
            return content_type != _MAIN_WORD_TYPE or part not in {None, "word/document.xml"}
    return False


def _word_attachment_errors(archive: zipfile.ZipFile, document, names: DeliverableNames) -> list[str]:
    errors: list[str] = []
    members = archive.namelist()
    if len(members) != len(set(members)):
        return ["duplicate Word package parts are not allowed"]
    content_types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
    ct_namespace = "{http://schemas.openxmlformats.org/package/2006/content-types}"
    if content_types.tag != ct_namespace + "Types":
        return ["invalid Word content-types manifest"]
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for declaration in content_types:
        content_type = declaration.get("ContentType", "").partition(";")[0].strip().casefold()
        part = None
        if declaration.tag == ct_namespace + "Override":
            part = unquote(declaration.get("PartName", "")).lstrip("/")
            overrides[part] = content_type
        elif declaration.tag == ct_namespace + "Default":
            defaults[declaration.get("Extension", "").casefold()] = content_type
        else:
            errors.append("invalid declaration in Word content-types manifest")
        if _attachment_content_type(content_type, part):
            errors.append(f"embedded attachment content type: {content_type} ({part or 'default'})")
    if overrides.get("word/document.xml", defaults.get("xml")) != _MAIN_WORD_TYPE:
        errors.append("participant main document content type is missing or invalid")

    for name in members:
        if name.casefold().startswith("word/embeddings/"):
            errors.append(f"embedded attachment is not part of the public pair: {name}")
        if name.endswith("/"):
            continue
        blob = archive.read(name)
        if blob.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")):
            errors.append(f"embedded attachment package/OLE bytes: {name}")
            continue
        extension = name.rsplit("/", 1)[-1].rsplit(".", 1)[-1].casefold()
        content_type = overrides.get(unquote(name), defaults.get(extension, ""))
        if name != "[Content_Types].xml" and _attachment_content_type(content_type, name):
            errors.append(f"embedded attachment content type: {content_type} ({name})")
        if not (
            extension in {"xml", "rels", "vml"}
            or content_type in {"application/xml", "text/xml", "application/vnd.openxmlformats-officedocument.vmldrawing"}
            or content_type.endswith("+xml")
        ):
            continue
        tree = document if name == "word/document.xml" else ElementTree.fromstring(blob)
        for node in tree.iter():
            namespace, _, local_name = node.tag.rpartition("}")
            local_name = local_name.casefold()
            if local_name in {"oleobject", "oleobj"} or (
                namespace.lstrip("{") in _WORD_NAMESPACES
                and local_name in {"object", "subdoc", "altchunk", "control"}
            ):
                errors.append(f"embedded attachment markup {node.tag} in {name}")
        if extension != "rels" and content_type != "application/vnd.openxmlformats-package.relationships+xml":
            continue
        for relation in tree:
            kind = relation.get("Type", "").rsplit("/", 1)[-1].casefold()
            if kind in _ATTACHMENT_RELATIONSHIPS:
                errors.append(f"embedded attachment relationship {kind} in {name}")
            if kind == "officedocument" and (
                name != "_rels/.rels"
                or unquote(relation.get("Target", "")).lstrip("/") != "word/document.xml"
            ):
                errors.append(f"embedded attachment subdocument relationship in {name}")
            if relation.get("TargetMode") == "External":
                problem = public_link_error(relation.get("Target", ""), names)
                if problem:
                    errors.append(problem)
    return errors


def public_word_errors(path: Path, names: DeliverableNames) -> list[str]:
    """Check the public-mode text and prohibit hidden attachments/companion links."""
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            document = ElementTree.fromstring(archive.read("word/document.xml"))
            text = "".join(
                node.text or ""
                for node in document.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
            )
            errors.extend(public_text_errors(text))
            errors.extend(_word_attachment_errors(archive, document, names))
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        errors.append(f"cannot inspect participant Word: {error}")
    return errors

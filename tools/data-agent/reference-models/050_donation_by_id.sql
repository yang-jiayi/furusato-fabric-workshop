CREATE FUNCTION agent_ref.DonationById
(
    @RequestedDonationId bigint
)
RETURNS TABLE
AS
RETURN
(
    SELECT
        CAST(@RequestedDonationId AS bigint) AS RequestedDonationId,
        CAST('exact-ID lookup' AS varchar(32)) AS RetrievalMode,
        donation.*
    FROM agent_ref.DonationAttributes
        AS donation
    WHERE @RequestedDonationId IS NOT NULL
      AND DonationId = @RequestedDonationId
);
GO

namespace OrderPipeline.Api.Services;

public sealed class OrderCalculator
{
    public decimal CalculateTotal(decimal unitPrice, int quantity, decimal discountPercent)
    {
        if (unitPrice < 0m)
            throw new ArgumentOutOfRangeException(nameof(unitPrice), "Unit price must not be negative.");

        if (quantity <= 0)
            throw new ArgumentOutOfRangeException(nameof(quantity), "Quantity must be greater than zero.");

        if (discountPercent is < 0m or > 100m)
            throw new ArgumentOutOfRangeException(nameof(discountPercent), "Discount must be between 0 and 100.");

        return decimal.Round(
            checked(unitPrice * quantity) * (1m - discountPercent / 100m),
            decimals: 2,
            mode: MidpointRounding.AwayFromZero);
    }
}

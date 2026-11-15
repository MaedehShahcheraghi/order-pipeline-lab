using Xunit;
using OrderPipeline.Api.Services;

namespace OrderPipeline.UnitTests;

public sealed class OrderCalculatorTests
{
    [Fact]
    public void ValidDiscount_ReturnsExpectedTotal()
    {
        var calculator = new OrderCalculator();
        var total = calculator.CalculateTotal(100m, 2, 10m);
        Assert.Equal(180m, total);
    }

    [Fact]
    public void DiscountAbove100_ThrowsArgumentOutOfRangeException()
    {
        var calculator = new OrderCalculator();
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            calculator.CalculateTotal(100m, 2, 150m));
    }
}

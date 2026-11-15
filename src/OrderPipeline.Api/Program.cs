using OrderPipeline.Api.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<OrderCalculator>();

var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));

app.MapGet("/version", () => Results.Ok(new
{
    service = "order-pipeline-lab",
    version = Environment.GetEnvironmentVariable("APP_VERSION") ?? "local",
    commit = Environment.GetEnvironmentVariable("GIT_SHA") ?? "unknown"
}));

app.MapPost("/orders/calculate", (CalculateOrderRequest request, OrderCalculator calculator) =>
{
    try
    {
        decimal total = calculator.CalculateTotal(
            request.UnitPrice, request.Quantity, request.DiscountPercent);
        return Results.Ok(new CalculateOrderResponse(total));
    }
    catch (ArgumentOutOfRangeException ex)
    {
        return Results.BadRequest(new { error = ex.Message, field = ex.ParamName });
    }
    catch (OverflowException)
    {
        return Results.BadRequest(new { error = "Calculation is too large." });
    }
});

app.Run();

public sealed record CalculateOrderRequest(decimal UnitPrice, int Quantity, decimal DiscountPercent);
public sealed record CalculateOrderResponse(decimal Total);

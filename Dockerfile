FROM mcr.microsoft.com/dotnet/sdk:10.0-alpine AS build
WORKDIR /source

COPY src/OrderPipeline.Api/OrderPipeline.Api.csproj src/OrderPipeline.Api/
RUN --mount=type=cache,target=/root/.nuget/packages \
    dotnet restore src/OrderPipeline.Api/OrderPipeline.Api.csproj

COPY src/OrderPipeline.Api/ src/OrderPipeline.Api/
ARG APP_VERSION=0.0.0-local
RUN --mount=type=cache,target=/root/.nuget/packages \
    dotnet publish src/OrderPipeline.Api/OrderPipeline.Api.csproj \
      --configuration Release --no-restore --output /app/publish \
      -p:Version="${APP_VERSION}" -p:UseAppHost=false -p:ContinuousIntegrationBuild=true

FROM mcr.microsoft.com/dotnet/aspnet:10.0-alpine AS final
WORKDIR /app
ARG APP_VERSION=0.0.0-local
ARG VCS_REF=unknown
ENV ASPNETCORE_URLS=http://+:8080 \
    DOTNET_RUNNING_IN_CONTAINER=true \
    APP_VERSION=${APP_VERSION} \
    GIT_SHA=${VCS_REF}
LABEL org.opencontainers.image.source="https://github.com/MaedehShahcheraghi/order-pipeline-lab" \
      org.opencontainers.image.title="order-pipeline-lab" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"
COPY --from=build /app/publish/ ./
USER $APP_UID
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1
ENTRYPOINT ["dotnet", "OrderPipeline.Api.dll"]

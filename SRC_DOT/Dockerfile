# Build stage
FROM mcr.microsoft.com/dotnet/sdk:10.0-preview AS build
WORKDIR /src

# Copy solution and project files first (better layer caching)
COPY OCRAdmissionForms.sln .
COPY OCRAdmissionForms.Core/OCRAdmissionForms.Core.csproj OCRAdmissionForms.Core/
COPY OCRAdmissionForms.Infrastructure/OCRAdmissionForms.Infrastructure.csproj OCRAdmissionForms.Infrastructure/
COPY OCRAdmissionForms.Web/OCRAdmissionForms.Web.csproj OCRAdmissionForms.Web/

# Restore dependencies
RUN dotnet restore OCRAdmissionForms.Web/OCRAdmissionForms.Web.csproj

# Copy everything else
COPY . .

# Publish release build
RUN dotnet publish OCRAdmissionForms.Web/OCRAdmissionForms.Web.csproj \
    -c Release \
    -o /app/publish \
    --no-restore

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0-preview AS runtime
WORKDIR /app

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Create uploads directory
RUN mkdir -p /app/uploads && chown -R appuser:appgroup /app/uploads

# Copy published output
COPY --from=build /app/publish .

# Set environment
ENV ASPNETCORE_ENVIRONMENT=Production
ENV PORT=8080
ENV ASPNETCORE_URLS=http://+:8080
ENV DOTNET_EnableDiagnostics=0

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Run as non-root
USER appuser

ENTRYPOINT ["dotnet", "OCRAdmissionForms.Web.dll"]

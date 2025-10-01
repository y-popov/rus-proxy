# ---- Build stage ----
FROM golang:1.24-alpine AS builder

# Install CA certificates (needed for HTTPS requests)
RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY go.mod .
RUN go mod download

COPY main.go .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux go build -o proxy .

# ---- Runtime stage ----
FROM scratch

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/proxy /proxy

# Run proxy
ENTRYPOINT ["/proxy"]

# Build stage
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum ./

# Use Chinese proxy for faster download in China
ENV GOPROXY=https://goproxy.cn,direct

RUN go mod download

# Copy source code
COPY . .

# Build the binary from cmd/api
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o StoryToVideoServer ./cmd/api

# Run stage
FROM alpine:3.19

WORKDIR /app

# Install ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates tzdata

# Set timezone
ENV TZ=Asia/Shanghai

# Copy binary and config
COPY --from=builder /app/StoryToVideoServer .
COPY --from=builder /app/config/config.yaml ./config/

# Expose port
EXPOSE 8080

CMD ["./StoryToVideoServer"]


package service

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/url"
	"path/filepath"
	"strings"
	"time"

	"StoryToVideo-server/internal/config"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

var MinioClient *minio.Client

// InitMinIO initializes MinIO connection
func InitMinIO() {
	cfg := config.AppConfig.MinIO
	var err error
	MinioClient, err = minio.New(cfg.Endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.AccessKey, cfg.SecretKey, ""),
		Secure: cfg.UseSSL,
	})
	if err != nil {
		log.Fatalf("MinIO 初始化失败: %v", err)
	}
	log.Println("MinIO 连接成功")
}

// UploadVideo uploads a local video file to MinIO
func UploadVideo(localPath string, taskID string) (string, error) {
	ctx := context.Background()
	cfg := config.AppConfig.MinIO
	bucketName := cfg.Bucket

	exists, err := MinioClient.BucketExists(ctx, bucketName)
	if err == nil && !exists {
		MinioClient.MakeBucket(ctx, bucketName, minio.MakeBucketOptions{})
	}

	objectName := fmt.Sprintf("tasks/%s/%s", taskID, filepath.Base(localPath))
	contentType := "video/mp4"

	_, err = MinioClient.FPutObject(ctx, bucketName, objectName, localPath, minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return "", fmt.Errorf("上传 MinIO 失败: %w", err)
	}

	expiry := time.Hour * 24
	reqParams := make(url.Values)

	presignedURL, err := MinioClient.PresignedGetObject(ctx, bucketName, objectName, expiry, reqParams)
	if err != nil {
		return "", fmt.Errorf("生成签名 URL 失败: %w", err)
	}

	finalURL := presignedURL.String()
	if cfg.Domain != "" {
		u, err := url.Parse(finalURL)
		if err == nil {
			domainURL, err := url.Parse(cfg.Domain)
			if err == nil {
				u.Scheme = domainURL.Scheme
				u.Host = domainURL.Host
				finalURL = u.String()
			}
		}
	}
	return finalURL, nil
}

// UploadToMinIO uploads from io.Reader to MinIO
func UploadToMinIO(reader io.Reader, objectName string, size int64) (string, error) {
	ctx := context.Background()
	cfg := config.AppConfig.MinIO
	bucketName := cfg.Bucket

	if objectName == "" {
		return "", fmt.Errorf("invalid object name: empty")
	}
	objectName = strings.TrimLeft(objectName, "/")
	objectName = strings.ReplaceAll(objectName, "\\", "/")
	if strings.Contains(objectName, "://") {
		return "", fmt.Errorf("invalid object name: contains URL scheme")
	}
	for i := 0; i < len(objectName); i++ {
		if objectName[i] < 32 {
			return "", fmt.Errorf("invalid object name: contains control characters")
		}
	}

	exists, err := MinioClient.BucketExists(ctx, bucketName)
	if err != nil {
		return "", fmt.Errorf("检查 Bucket 失败: %w", err)
	}
	if !exists {
		err = MinioClient.MakeBucket(ctx, bucketName, minio.MakeBucketOptions{})
		if err != nil {
			return "", fmt.Errorf("创建 Bucket 失败: %w", err)
		}
		log.Printf("Bucket '%s' 已创建", bucketName)
	}

	contentType := "application/octet-stream"
	ext := filepath.Ext(objectName)
	switch ext {
	case ".jpg", ".jpeg":
		contentType = "image/jpeg"
	case ".png":
		contentType = "image/png"
	case ".webp":
		contentType = "image/webp"
	case ".mp4":
		contentType = "video/mp4"
	case ".mp3":
		contentType = "audio/mpeg"
	case ".wav":
		contentType = "audio/wav"
	}

	_, err = MinioClient.PutObject(ctx, bucketName, objectName, reader, size, minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return "", fmt.Errorf("上传到 MinIO 失败: %w", err)
	}

	expiry := time.Hour * 72
	reqParams := make(url.Values)

	presignedURL, err := MinioClient.PresignedGetObject(ctx, bucketName, objectName, expiry, reqParams)
	if err != nil {
		return "", fmt.Errorf("生成签名 URL 失败: %w", err)
	}

	finalURL := presignedURL.String()
	if cfg.Domain != "" {
		u, err := url.Parse(finalURL)
		if err == nil {
			domainURL, err := url.Parse(cfg.Domain)
			if err == nil {
				u.Scheme = domainURL.Scheme
				u.Host = domainURL.Host
				finalURL = u.String()
			}
		}
	}

	log.Printf("文件已上传: %s", objectName)
	return finalURL, nil
}

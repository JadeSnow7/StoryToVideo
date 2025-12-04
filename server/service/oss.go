package service

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/url"
	"path/filepath"
	"time"

	"StoryToVideo-server/config"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

var MinioClient *minio.Client

// InitMinIO 初始化连接，在 main.go 中调用
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

// UploadVideo 上传本地视频文件到 MinIO，返回可访问的 URL
func UploadVideo(localPath string, taskID string) (string, error) {
	ctx := context.Background()
	cfg := config.AppConfig.MinIO
	bucketName := cfg.Bucket

    // 自动创建 Bucket
	exists, err := MinioClient.BucketExists(ctx, bucketName)
	if err == nil && !exists {
		MinioClient.MakeBucket(ctx, bucketName, minio.MakeBucketOptions{})
	}

    // 生成云端文件名，例如: tasks/123-abc/output.mp4
	objectName := fmt.Sprintf("tasks/%s/%s", taskID, filepath.Base(localPath))
	contentType := "video/mp4"

    // 执行上传
	_, err = MinioClient.FPutObject(ctx, bucketName, objectName, localPath, minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return "", fmt.Errorf("上传 MinIO 失败: %w", err)
	}

	expiry := time.Hour * 24
	reqParams := make(url.Values)
    // 如果需要强制下载
    // reqParams.Set("response-content-disposition", "attachment; filename=\""+filepath.Base(localPath)+"\"")

    presignedURL, err := MinioClient.PresignedGetObject(ctx, bucketName, objectName, expiry, reqParams)
    if err != nil {
        return "", fmt.Errorf("生成签名 URL 失败: %w", err)
    }

    return presignedURL.String(), nil // 修改这里：返回 presignedURL.String()
}

// UploadToMinIO 通用上传函数，从 io.Reader 上传到 MinIO，返回可访问的 URL
// 参数:
//   - reader: 文件数据流 (可以是 http.Response.Body 或其他 io.Reader)
//   - objectName: 云端存储路径，例如 "shots/123/image.png"
//   - size: 文件大小（字节），-1 表示未知大小
func UploadToMinIO(reader io.Reader, objectName string, size int64) (string, error) {
	ctx := context.Background()
	cfg := config.AppConfig.MinIO
	bucketName := cfg.Bucket

	// 确保 Bucket 存在
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

	// 根据文件扩展名确定 ContentType
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

	// 上传文件
	_, err = MinioClient.PutObject(ctx, bucketName, objectName, reader, size, minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return "", fmt.Errorf("上传到 MinIO 失败: %w", err)
	}

	// 生成预签名 URL（24小时有效期）
	expiry := time.Hour * 72
	reqParams := make(url.Values)
	
	presignedURL, err := MinioClient.PresignedGetObject(ctx, bucketName, objectName, expiry, reqParams)
	if err != nil {
		return "", fmt.Errorf("生成签名 URL 失败: %w", err)
	}

	log.Printf("文件已上传: %s", objectName)
	return presignedURL.String(), nil // 修改这里：返回 presignedURL.String()
}
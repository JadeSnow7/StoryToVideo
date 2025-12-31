package config

import (
    "log"
    "os"

    "gopkg.in/yaml.v2"
)

type Config struct {
    Server struct {
        Port string `yaml:"port"`
    } `yaml:"server"`
    MySQL struct {
        DSN string `yaml:"dsn"`
    } `yaml:"mysql"`
    AI struct {
        ImageAPI string `yaml:"image_api"`
        VoiceAPI string `yaml:"voice_api"`
    } `yaml:"ai"`

    Redis struct {
        Addr     string `yaml:"addr"`
        Password string `yaml:"password"`
    } `yaml:"redis"`
    Worker struct {
        Addr string `yaml:"addr"` 
    } `yaml:"worker"`
    MinIO struct {
        Endpoint  string `yaml:"endpoint"`
        AccessKey string `yaml:"access_key"`
        SecretKey string `yaml:"secret_key"`
        Bucket    string `yaml:"bucket"`
        UseSSL    bool   `yaml:"use_ssl"`
        Domain    string `yaml:"domain"`
    } `yaml:"minio"`
}

var AppConfig *Config

func InitConfig() {
    f, err := os.Open("config/config.yaml")
    if err != nil {
        log.Fatalf("配置文件读取失败: %v", err)
    }
    defer f.Close()
    decoder := yaml.NewDecoder(f)
    AppConfig = &Config{}
    if err := decoder.Decode(AppConfig); err != nil {
        log.Fatalf("配置文件解析失败: %v", err)
    }
}
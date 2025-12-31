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
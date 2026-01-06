// Package models provides data models and database operations.
package models

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"strings"
	"time"

	"StoryToVideo-server/internal/config"

	_ "github.com/go-sql-driver/mysql"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

var DB *sql.DB
var GormDB *gorm.DB

func InitDB() {
	if config.AppConfig == nil {
		log.Fatal("config.AppConfig is nil, call config.InitConfig first")
	}
	dsn := config.AppConfig.MySQL.DSN
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		log.Fatalf("打开数据库失败: %v", err)
	}
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(time.Hour)

	if err := db.Ping(); err != nil {
		log.Fatalf("连接数据库失败: %v", err)
	}

	DB = db
	GormDB, err = gorm.Open(mysql.New(mysql.Config{
		Conn: DB,
	}), &gorm.Config{})
	if err != nil {
		log.Fatalf("GORM 初始化失败: %v", err)
	}

	log.Println("数据库连接成功 (Native SQL + GORM)")

	// 自动建表（读取 doc/sql/StoryToVideo.sql）
	b, err := ioutil.ReadFile("doc/sql/StoryToVideo.sql")
	if err != nil {
		log.Printf("读取 SQL 文件失败（跳过建表）: %v", err)
		return
	}
	sqls := strings.Split(string(b), ";")
	for _, s := range sqls {
		s = strings.TrimSpace(s)
		if s == "" {
			continue
		}
		if _, err := DB.Exec(s); err != nil {
			log.Printf("执行建表语句失败: %v ; sql: %s", err, s)
		}
	}
}

// Project CRUD
func CreateProject(p *Project) error {
	now := time.Now()
	p.CreatedAt = now
	p.UpdatedAt = now
	_, err := DB.Exec(
		`INSERT INTO project (id, title, story_text, style, status, cover_image, duration, video_url, description, shot_count, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		p.ID, p.Title, p.StoryText, p.Style, p.Status, p.CoverImage, p.Duration, p.VideoUrl, p.Description, p.ShotCount, p.CreatedAt, p.UpdatedAt,
	)
	return err
}

func GetProjectByID(id string) (Project, error) {
	var p Project
	row := DB.QueryRow(`SELECT id, title, story_text, style, status, cover_image, duration, video_url, description, shot_count, created_at, updated_at FROM project WHERE id = ?`, id)
	var createdAt, updatedAt time.Time
	if err := row.Scan(&p.ID, &p.Title, &p.StoryText, &p.Style, &p.Status, &p.CoverImage, &p.Duration, &p.VideoUrl, &p.Description, &p.ShotCount, &createdAt, &updatedAt); err != nil {
		return p, err
	}
	p.CreatedAt = createdAt
	p.UpdatedAt = updatedAt
	return p, nil
}

func UpdateProjectByID(id string, title, description string) error {
	_, err := DB.Exec(`UPDATE project SET title = ?, description = ?, updated_at = ? WHERE id = ?`, title, description, time.Now(), id)
	return err
}

func DeleteProjectByID(id string) error {
	_, err := DB.Exec(`DELETE FROM project WHERE id = ?`, id)
	return err
}

// Shot CRUD
func CreateShot(s *Shot) error {
	now := time.Now()
	s.CreatedAt = now
	s.UpdatedAt = now
	_, err := DB.Exec(
		`INSERT INTO shot (id, project_id, `+"`order`"+`, title, description, prompt, status, image_path, transition, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		s.ID, s.ProjectId, s.Order, s.Title, s.Description, s.Prompt, s.Status, s.ImagePath, s.Transition, s.CreatedAt, s.UpdatedAt,
	)
	return err
}

func GetShotsByProjectID(projectID string) ([]Shot, error) {
	rows, err := DB.Query(`SELECT id, project_id, `+"`order`"+`, title, description, prompt, status, image_path, transition, created_at, updated_at FROM shot WHERE project_id = ? ORDER BY `+"`order`"+` ASC`, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var res []Shot
	for rows.Next() {
		var s Shot
		var createdAt, updatedAt time.Time
		if err := rows.Scan(&s.ID, &s.ProjectId, &s.Order, &s.Title, &s.Description, &s.Prompt, &s.Status, &s.ImagePath, &s.Transition, &createdAt, &updatedAt); err != nil {
			return nil, err
		}
		s.CreatedAt = createdAt
		s.UpdatedAt = updatedAt
		res = append(res, s)
	}
	return res, nil
}

func GetShotByID(projectID, shotID string) (Shot, error) {
	var s Shot
	row := DB.QueryRow(`SELECT id, project_id, `+"`order`"+`, title, description, prompt, status, image_path, transition, created_at, updated_at FROM shot WHERE id = ? AND project_id = ?`, shotID, projectID)
	var createdAt, updatedAt time.Time
	if err := row.Scan(&s.ID, &s.ProjectId, &s.Order, &s.Title, &s.Description, &s.Prompt, &s.Status, &s.ImagePath, &s.Transition, &createdAt, &updatedAt); err != nil {
		return s, err
	}
	s.CreatedAt = createdAt
	s.UpdatedAt = updatedAt
	return s, nil
}

func DeleteShotByID(projectID, shotID string) error {
	_, err := DB.Exec(`DELETE FROM shot WHERE id = ? AND project_id = ?`, shotID, projectID)
	return err
}

// Task create helper
func CreateTask(t *Task) error {
	now := time.Now()
	t.CreatedAt = now
	t.UpdatedAt = now

	params, _ := json.Marshal(t.Parameters)
	result, _ := json.Marshal(t.Result)

	var startedAtParam interface{}
	if t.StartedAt.IsZero() {
		startedAtParam = nil
	} else {
		startedAtParam = t.StartedAt
	}
	var finishedAtParam interface{}
	if t.FinishedAt.IsZero() {
		finishedAtParam = nil
	} else {
		finishedAtParam = t.FinishedAt
	}

	_, err := DB.Exec(`INSERT INTO task (id, project_id, type, status, progress, message, parameters, result, error, estimated_duration, started_at, finished_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		t.ID, t.ProjectId, t.Type, t.Status, t.Progress, t.Message, params, result, t.Error, t.EstimatedDuration, startedAtParam, finishedAtParam, t.CreatedAt, t.UpdatedAt,
	)
	return err
}

func UpdateShotByID(projectID, shotID, title, prompt, transition string) error {
	sets := []string{}
	args := []interface{}{}
	if title != "" {
		sets = append(sets, "title = ?")
		args = append(args, title)
	}
	if prompt != "" {
		sets = append(sets, "prompt = ?")
		args = append(args, prompt)
	}
	if transition != "" {
		sets = append(sets, "transition = ?")
		args = append(args, transition)
	}
	if len(sets) == 0 {
		return nil
	}
	query := fmt.Sprintf("UPDATE shot SET %s, updated_at = ? WHERE id = ? AND project_id = ?", strings.Join(sets, ", "))
	args = append(args, time.Now(), shotID, projectID)
	_, err := DB.Exec(query, args...)
	return err
}

func GetTaskByID(id string) (Task, error) {
	var t Task
	row := DB.QueryRow(`SELECT id, project_id, shot_id, type, status, progress, message, parameters, result, error, estimated_duration, started_at, finished_at, created_at, updated_at FROM task WHERE id = ?`, id)

	var paramsBytes, resultBytes []byte
	var startedAt, finishedAt, createdAt, updatedAt sql.NullTime
	var shotIDNull sql.NullString
	var messageNull sql.NullString
	var errorNull sql.NullString

	if err := row.Scan(&t.ID, &t.ProjectId, &shotIDNull, &t.Type, &t.Status, &t.Progress, &messageNull, &paramsBytes, &resultBytes, &errorNull, &t.EstimatedDuration, &startedAt, &finishedAt, &createdAt, &updatedAt); err != nil {
		return t, err
	}

	if messageNull.Valid {
		t.Message = messageNull.String
	} else {
		t.Message = ""
	}
	if errorNull.Valid {
		t.Error = errorNull.String
	} else {
		t.Error = ""
	}

	_ = json.Unmarshal(paramsBytes, &t.Parameters)
	_ = json.Unmarshal(resultBytes, &t.Result)

	if startedAt.Valid {
		t.StartedAt = startedAt.Time
	}
	if finishedAt.Valid {
		t.FinishedAt = finishedAt.Time
	}
	if createdAt.Valid {
		t.CreatedAt = createdAt.Time
	}
	if updatedAt.Valid {
		t.UpdatedAt = updatedAt.Time
	}
	return t, nil
}

// UpdateTaskStatus updates task fields dynamically
func UpdateTaskStatus(id string, status string, progress *int, message *string, result *TaskResult, errStr *string, startedAt *time.Time, finishedAt *time.Time) error {
	sets := []string{}
	args := []interface{}{}

	if status != "" {
		sets = append(sets, "status = ?")
		args = append(args, status)
	}
	if progress != nil {
		sets = append(sets, "progress = ?")
		args = append(args, *progress)
	}
	if message != nil {
		sets = append(sets, "message = ?")
		args = append(args, *message)
	}
	if result != nil {
		b, _ := json.Marshal(result)
		sets = append(sets, "result = ?")
		args = append(args, b)
	}
	if errStr != nil {
		sets = append(sets, "error = ?")
		args = append(args, *errStr)
	}
	if startedAt != nil {
		sets = append(sets, "started_at = ?")
		args = append(args, *startedAt)
	}
	if finishedAt != nil {
		sets = append(sets, "finished_at = ?")
		args = append(args, *finishedAt)
	}

	if len(sets) == 0 {
		_, err := DB.Exec(`UPDATE task SET updated_at = ? WHERE id = ?`, time.Now(), id)
		return err
	}

	sets = append(sets, "updated_at = ?")
	args = append(args, time.Now())

	query := fmt.Sprintf("UPDATE task SET %s WHERE id = ?", strings.Join(sets, ", "))
	args = append(args, id)

	_, err := DB.Exec(query, args...)
	return err
}

-- ...existing code...
-- 测试数据：1 project + 3 shots + 多个 tasks（所有 task 状态均为 finished）

-- 1) 测试 project（项目状态设为 ready）
INSERT INTO project (id, title, story_text, style, status, cover_image, duration, video_url, description, shot_count, created_at, updated_at)
VALUES (
  'proj-test-0001',
  '测试项目 - 全量已完成',
  '这是一个用于前端联调的示例项目，故事文本已生成。',
  '默认风格',
  'ready',
  '',
  0,
  '',
  '用于前端接口联调的测试项目（全部任务均为 finished）',
  3,
  NOW(),
  NOW()
);

-- 2) 三个测试 shot（均已完成图片）
INSERT INTO shot (id, project_id, `order`, title, description, prompt, status, image_path, audio_path, transition, created_at, updated_at)
VALUES
  ('shot-test-0001', 'proj-test-0001', 1, '镜头 1', '描述 1', '主角走进房间', 'completed', '/static/tasks/123/shot-0001.png', '', 'cut', NOW(), NOW()),
  ('shot-test-0002', 'proj-test-0001', 2, '镜头 2', '描述 2', '主角发现画不见了', 'completed', '/static/tasks/123/shot-0002.png', '', 'fade', NOW(), NOW()),
  ('shot-test-0003', 'proj-test-0001', 3, '镜头 3', '描述 3', '主角打开抽屉', 'completed', '/static/tasks/123/shot-0003.png', '', 'cut', NOW(), NOW());

-- 3) project_text（finished）
INSERT INTO task (id, project_id, shot_id, type, status, progress, message, parameters, result, error, estimated_duration, started_at, finished_at, created_at, updated_at)
VALUES (
  'task-text-test-0001',
  'proj-test-0001',
  NULL,
  'project_text',
  'finished',
  100,
  '项目文本已生成',
  '{"shot_defaults":{"shot_count":3,"style":"默认风格","storyText":"示例故事文本"}}',
  '{"resource_type":"project","resource_id":"proj-test-0001","resource_url":""}',
  '',
  0,
  NOW() - INTERVAL 5 MINUTE,
  NOW() - INTERVAL 4 MINUTE,
  NOW() - INTERVAL 5 MINUTE,
  NOW() - INTERVAL 4 MINUTE
);

-- 4) 三个 shot_image（均 finished）
INSERT INTO task (id, project_id, shot_id, type, status, progress, message, parameters, result, error, estimated_duration, started_at, finished_at, created_at, updated_at)
VALUES
  ('task-shot-test-0001','proj-test-0001','shot-test-0001','shot_image','finished',100,'已生成镜头1图片','{\"shot\":{\"shotId\":\"shot-test-0001\",\"prompt\":\"主角走进房间\",\"transition\":\"cut\",\"image_width\":1024,\"image_height\":1024},\"depends_on\":\"task-text-test-0001\"}','{\"resource_type\":\"shot\",\"resource_id\":\"shot-test-0001\",\"resource_url\":\"/static/tasks/123/shot-test-0001.png\"}','',0,NOW() - INTERVAL 4 MINUTE,NOW() - INTERVAL 3 MINUTE,NOW() - INTERVAL 4 MINUTE,NOW() - INTERVAL 3 MINUTE),
  ('task-shot-test-0002','proj-test-0001','shot-test-0002','shot_image','finished',100,'已生成镜头2图片','{\"shot\":{\"shotId\":\"shot-test-0002\",\"prompt\":\"主角发现画不见了\",\"transition\":\"fade\",\"image_width\":1024,\"image_height\":1024},\"depends_on\":\"task-text-test-0001\"}','{\"resource_type\":\"shot\",\"resource_id\":\"shot-test-0002\",\"resource_url\":\"/static/tasks/123/shot-test-0002.png\"}','',0,NOW() - INTERVAL 4 MINUTE,NOW() - INTERVAL 3 MINUTE,NOW() - INTERVAL 4 MINUTE,NOW() - INTERVAL 3 MINUTE),
  ('task-shot-test-0003','proj-test-0001','shot-test-0003','shot_image','finished',100,'已生成镜头3图片','{\"shot\":{\"shotId\":\"shot-test-0003\",\"prompt\":\"主角打开抽屉\",\"transition\":\"cut\",\"image_width\":1024,\"image_height\":1024},\"depends_on\":\"task-text-test-0001\"}','{\"resource_type\":\"shot\",\"resource_id\":\"shot-test-0003\",\"resource_url\":\"/static/tasks/123/shot-test-0003.png\"}','',0,NOW() - INTERVAL 4 MINUTE,NOW() - INTERVAL 3 MINUTE,NOW() - INTERVAL 4 MINUTE,NOW() - INTERVAL 3 MINUTE);

-- 5) project_video（finished）
INSERT INTO task (id, project_id, shot_id, type, status, progress, message, parameters, result, error, estimated_duration, started_at, finished_at, created_at, updated_at)
VALUES (
  'task-video-test-0001',
  'proj-test-0001',
  NULL,
  'project_video',
  'finished',
  100,
  '项目视频生成完成',
  '{"video":{"resolution":"1920x1080","fps":30,"format":"mp4","bitrate":4000}}',
  '{"resource_type":"video","resource_id":"proj-test-0001","resource_url":"/static/tasks/123/proj-test-0001.mp4"}',
  '',
  0,
  NOW() - INTERVAL 3 MINUTE,
  NOW() - INTERVAL 2 MINUTE,
  NOW() - INTERVAL 3 MINUTE,
  NOW() - INTERVAL 2 MINUTE
);

-- 6) project_audio（finished）
INSERT INTO task (id, project_id, shot_id, type, status, progress, message, parameters, result, error, estimated_duration, started_at, finished_at, created_at, updated_at)
VALUES (
  'task-audio-test-0001',
  'proj-test-0001',
  NULL,
  'project_audio',
  'finished',
  100,
  '项目配音生成完成',
  '{"tts":{"voice":"xiaoyan","lang":"zh-CN","sample_rate":24000,"format":"mp3"}}',
  '{"resource_type":"audio","resource_id":"proj-test-0001","resource_url":"/static/tasks/123/proj-test-0001.mp3"}',
  '',
  0,
  NOW() - INTERVAL 3 MINUTE,
  NOW() - INTERVAL 2 MINUTE,
  NOW() - INTERVAL 3 MINUTE,
  NOW() - INTERVAL 2 MINUTE
);
-- ...existing code...mysql -u root -p story_to_video < doc/sql/test_data.sqlmysql -u root -p story_to_video < doc/sql/test_data.sql
import websocket

def on_message(ws, message):
    print(f"收到消息: {message}")

def on_error(ws, error):
    print(f"错误: {error}")

def on_close(ws, close_status_code, close_msg):
    print("连接关闭")

def on_open(ws):
    print("连接成功")
    # 可以发送测试消息
    ws.send("Hello Server")

if __name__ == "__main__":
    ws = websocket.WebSocketApp("ws://119.45.124.222:8080/tasks/124/wss",
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    ws.run_forever()
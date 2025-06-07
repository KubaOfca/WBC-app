from website import create_app, socket

app = create_app()

if __name__ == "__main__":
    socket.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)

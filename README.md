# MT5 Framework Quantdemy

This project provides an example institutional trading bot built on top of MetaTrader5.

## Environment Variables

Create a `.env` file in the project root (you can base it on `.env.example`) with the following values:

- `OLLAMA_API_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TWELVEDATA_API_KEY`
- `MT5_PATH`
- `MT5_LOGIN`
- `MT5_PASSWORD`
- `MT5_SERVER`
- `MT5_TIMEOUT`
- `MT5_PORTABLE`

These variables are loaded at startup so credentials remain outside version control.

FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 poppler-utils ca-certificates git \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @anthropic-ai/claude-code \
 && npm cache clean --force

# App code is owned by root and read-only to the bot user, so Claude cannot
# edit the Smokeball client (and its no-DELETE guard) from inside a task.
COPY bot.py smokeball.py /app/
RUN chmod 0755 /app && chmod 0644 /app/*.py

RUN useradd -m -u 1001 sfl && mkdir -p /workspace /state && chown sfl:sfl /workspace /state
USER sfl
WORKDIR /workspace

CMD ["python3", "-u", "/app/bot.py"]

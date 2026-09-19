# Start from a small official Python image.
# "slim" = minimal Linux with Python, much smaller than the full image.
FROM python:3.12-slim

# Everything after this happens inside /app in the container.
WORKDIR /app

# Copy ONLY requirements first. Docker caches each step, so as long as
# this file doesn't change, it will reuse the installed libraries
# instead of re-downloading them on every build. Big time saver.
COPY requirements.txt .

# Install the libraries.
# --no-cache-dir keeps the image smaller.
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code.
COPY ./app ./app

# Document which port this container listens on.
EXPOSE 8000

# The command that runs when the container starts.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
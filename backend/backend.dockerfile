FROM fba_base_server

WORKDIR /fba

COPY . .

RUN mv backend/.env.docker /fba/backend/.env

CMD ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]
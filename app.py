import os
import smtplib
from email.message import EmailMessage

from flask import Flask, jsonify, request
from mssql_python import connect

app = Flask(__name__)


def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    port = os.getenv("DB_PORT", "1433")

    if not server:
        raise ValueError("Falta DB_SERVER")
    if not database:
        raise ValueError("Falta DB_DATABASE")
    if not username:
        raise ValueError("Falta DB_USERNAME")
    if not password:
        raise ValueError("Falta DB_PASSWORD")

    connection_string = (
        f"Server=tcp:{server},{port};"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Authentication=SqlPassword;"
    )

    return connect(connection_string)


@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "API Flask funcionando correctamente en Render"
    })


@app.route("/debug-env")
def debug_env():
    return jsonify({
        "DB_SERVER": os.getenv("DB_SERVER"),
        "DB_DATABASE": os.getenv("DB_DATABASE"),
        "DB_USERNAME": os.getenv("DB_USERNAME"),
        "DB_PASSWORD_EXISTS": bool(os.getenv("DB_PASSWORD")),
        "DB_PORT": os.getenv("DB_PORT"),
    })


@app.route("/test-db")
def test_db():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT GETDATE() AS fecha_servidor")
        row = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Conexión a SQL Server exitosa",
            "server_date": str(row[0])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error al conectar con SQL Server",
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/productos")
def listar_productos():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 20 Id, Nombre, Precio, Stock, Version, Imagen
            FROM Productos
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "nombre": row[1],
                "precio": float(row[2]) if row[2] is not None else None,
                "stock": row[3],
                "version": row[4],
                "imagen_url": row[5],
            })

        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error al consultar productos",
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def enviar_correo_alerta(asunto, mensaje, destino):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("EMAIL_USER")
    smtp_password = os.getenv("EMAIL_PASSWORD")
    smtp_from = os.getenv("EMAIL_FROM", smtp_username)
    smtp_use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    smtp_starttls = os.getenv("SMTP_STARTTLS", "true").lower() == "true"

    if not smtp_host:
        raise ValueError("Falta SMTP_HOST")
    if not smtp_username:
        raise ValueError("Falta EMAIL_USER")
    if not smtp_password:
        raise ValueError("Falta EMAIL_PASSWORD")
    if not smtp_from:
        raise ValueError("Falta EMAIL_FROM")

    email = EmailMessage()
    email["Subject"] = asunto
    email["From"] = smtp_from
    email["To"] = destino
    email.set_content(mensaje)

    if smtp_use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(email)
        return

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if smtp_starttls:
            server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(email)

@app.route("/enviar-alerta", methods=["POST"]) 
def enviar_alerta():
    try:
        data = request.get_json()
        destino = data.get("to")
        asunto = data.get("subject")
        mensaje = data.get("message")

        if not destino or not asunto or not mensaje:
            return jsonify({
                "success": False,
                "message": "Faltan datos"
            }), 400

        enviar_correo_alerta(asunto, mensaje, destino)
        return jsonify({
            "success": True,
            "message": "Correo enviado"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
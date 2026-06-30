from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Egreso, FormaPago, Usuario  # <-- Agregamos Usuario aquí
from config import Config
from werkzeug.security import check_password_hash # <-- Para validar la clave encriptada
from flask_login import LoginManager, login_user, logout_user, login_required, current_user # <-- Sistema de login

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar la base de datos
db.init_app(app)

# --- CONFIGURACIÓN DE FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Si alguien no está logueado, lo manda aquí
login_manager.login_message = "Por favor, inicia sesión para acceder al sistema."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

with app.app_context():
    db.create_all()


# --- RUTAS DE AUTENTICACIÓN ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password")

        usuario = Usuario.query.filter_by(username=username).first()

        # Comparamos la contraseña plana con el hash de la BD
        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            flash(f"¡Bienvenido, {usuario.nombre}!", "success")
            return redirect(url_for("inicio"))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("login"))


# --- RUTAS DEL CRUD (PROTEGIDAS CON @login_required) ---

@app.route("/")
@login_required # <-- Bloquea el acceso si no inició sesión
def inicio():
    egresos = Egreso.query.order_by(Egreso.fecha.desc()).all()
    return render_template("index.html", egresos=egresos)

@app.route("/crear", methods=["GET", "POST"])
@login_required
def crear_egreso():
    if request.method == "POST":
        detalle = request.form.get("detalle")
        monto = request.form.get("monto")
        idformapago = request.form.get("idformapago")

        if not detalle or not monto or not idformapago:
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("crear_egreso"))

        try:
            nuevo_egreso = Egreso(
                detalle=detalle,
                monto=float(monto),
                idformapago=int(idformapago)
            )
            db.session.add(nuevo_egreso)
            db.session.commit()
            flash("Egreso registrado correctamente.", "success")
            return redirect(url_for("inicio"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar el egreso: {str(e)}", "danger")
            return redirect(url_for("crear_egreso"))

    formas_pago = FormaPago.query.filter_by(estado=1).all()
    return render_template("crear.html", formas_pago=formas_pago)

@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_egreso(id):
    egreso = Egreso.query.get_or_404(id)
    if request.method == "POST":
        egreso.detalle = request.form.get("detalle")
        egreso.monto = float(request.form.get("monto"))
        egreso.idformapago = int(request.form.get("idformapago"))
        try:
            db.session.commit()
            flash("Egreso actualizado correctamente.", "success")
            return redirect(url_for("inicio"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el egreso: {str(e)}", "danger")
            return redirect(url_for("editar_egreso", id=id))

    formas_pago = FormaPago.query.filter_by(estado=1).all()
    return render_template("editar.html", egreso=egreso, formas_pago=formas_pago)

@app.route("/eliminar/<int:id>", methods=["POST", "GET"])
@login_required
def eliminar_egreso(id):
    egreso = Egreso.query.get_or_404(id)
    try:
        db.session.delete(egreso)
        db.session.commit()
        flash("Egreso eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el egreso: {str(e)}", "danger")
    return redirect(url_for("inicio"))

@app.route("/buscar", methods=["GET", "POST"])
@login_required
def buscar_egreso():
    egresos = []
    criterio = ""
    if request.method == "POST":
        criterio = request.form.get("criterio", "").strip()
        if criterio:
            egresos = Egreso.query.filter(Egreso.detalle.ilike(f"%{criterio}%")).order_by(Egreso.fecha.desc()).all()
        else:
            egresos = Egreso.query.order_by(Egreso.fecha.desc()).all()
    return render_template("buscar.html", egresos=egresos, criterio=criterio)
# ==========================================
#         SERVICIOS WEB / API REST
# ==========================================

@app.route("/api/egresos", methods=["GET"])
def api_lista_egresos():
    """Retorna todos los egresos en formato JSON para servicios externos"""
    try:
        egresos = Egreso.query.order_by(Egreso.fecha.desc()).all()
        lista_json = [egreso.to_dict() for egreso in egresos]

        return jsonify({
            "status": "success",
            "total_registros": len(lista_json),
            "data": lista_json
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error al recuperar datos: {str(e)}"
        }), 500

@app.route("/api/egresos", methods=["POST"])
def api_crear_egreso():
    """Recibe un JSON externo y registra un nuevo egreso en la BD"""
    datos = request.get_json()

    if not datos:
        return jsonify({"status": "error", "message": "No se proporcionaron datos en formato JSON"}), 400

    detalle = datos.get("detalle")
    monto = datos.get("monto")
    idformapago = datos.get("idformapago")

    if not detalle or not monto or not idformapago:
        return jsonify({"status": "error", "message": "Faltan campos obligatorios: detalle, monto o idformapago"}), 400

    try:
        nuevo_egreso = Egreso(
            detalle=detalle,
            monto=float(monto),
            idformapago=int(idformapago)
        )
        db.session.add(nuevo_egreso)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Egreso registrado mediante API de forma exitosa",
            "data": nuevo_egreso.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Error en el servidor: {str(e)}"}), 500
@app.route("/crear-usuario-admin-temporal")
def crear_usuario_temporal():
    """Ruta temporal para forzar la creación del admin en Render gratis"""
    try:
        # Verificamos si ya existe para no duplicarlo
        existe = Usuario.query.filter_by(username="admin").first()
        if existe:
            return "El usuario admin ya existe en la base de datos.", 200
            
        u = Usuario(
            username='admin', 
            password_hash='scrypt:32768:8:1$gw3GwaRypiOwPyWu$d472106bd7ae1576b9a755a1916d9276262c9e580209f1e6fc09c94fe8bffc84712e21053f7698e1efeb05528fce3e0e58f5ab1d8181a59a2f884157286329ca', 
            nombre='Kevin Administrador'
        )
        db.session.add(u)
        db.session.commit()
        return "¡Usuario admin creado con éxito en la nube!", 201
    except Exception as e:
        return f"Error al crear el usuario: {str(e)}", 500
        
@app.route("/configurar-bd-temporal")
def configurar_bd_temporal():
    """Ruta temporal para insertar el admin y las formas de pago en Render"""
    try:
        # 1. Insertar formas de pago si la tabla está vacía
        if FormaPago.query.count() == 0:
            efectivo = FormaPago(nombre="Efectivo", estado=1)
            tarjeta = FormaPago(nombre="Tarjeta", estado=1)
            qr = FormaPago(nombre="Código QR", estado=1)
            db.session.add_all([efectivo, tarjeta, qr])
            
        # 2. Insertar usuario si no existe
        if not Usuario.query.filter_by(username="admin").first():
            u = Usuario(
                username='admin', 
                password_hash='scrypt:32768:8:1$gw3GwaRypiOwPyWu$d472106bd7ae1576b9a755a1916d9276262c9e580209f1e6fc09c94fe8bffc84712e21053f7698e1efeb05528fce3e0e58f5ab1d8181a59a2f884157286329ca', 
                nombre='Kevin Administrador'
            )
            db.session.add(u)
            
        db.session.commit()
        return "¡Base de datos configurada con éxito en la nube!", 200
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

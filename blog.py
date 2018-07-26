from flask import Flask,render_template,flash,redirect,url_for,session,logging,request,g
from flask_mysqldb import MySQL
from wtforms import Form,TextAreaField,PasswordField,validators,StringField
from passlib.hash import sha256_crypt
from functools import wraps



#kullanıcı giriş decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
       if "logged_in" in session:
            return f(*args, **kwargs)
       else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın...","danger")
            return redirect(url_for("login"))
    return decorated_function



#kullanıcı kayıt formu
class registerForm(Form):
    name = StringField("Adınız: ", validators=[validators.Length(min=4,max=25)])
    userName = StringField("Kullanıcı Adınız: ", validators=[validators.Length(min=4,max=25)])
    email = StringField("Email Adresiniz: ", validators=[validators.Email(message="geçerli bir mail girin")])
    password = PasswordField("Parola: ", validators=[
        validators.DataRequired(message= "Bu alan boş bırakılamaz."),
        validators.EqualTo(fieldname= "confirm", message="Parolalar uyuşmamaktadır.")
    ])
    confirm = PasswordField("Parola Doğrula: ")


#login için oluşturduğumuz class
class loginForm(Form):
    userName = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

#makale formu için oluşturduğumuz class
class articleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(min=7,max=50)])
    content = TextAreaField("Makale içeriği",validators=[validators.length(min=25)])



app = Flask(__name__)


app.secret_key = "myblog"

#mysql bağlantısını sağlamak için yapılması gereken config işlemleri
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "myBlog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

#mysql bağlantısı için yapılan tanımlama
mysql = MySQL(app)

#anasayfamıza giden kısım
@app.route("/")
def index():
    return render_template("index.html")


#hakkımızda sayfası
@app.route("/about")
def about():
    return render_template("about.html")


#makaleleri göstermek için
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    makaleGösterme = "Select * from articles"

    result = cursor.execute(makaleGösterme)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")


#kontrol panelimize giriş yapmak için yapılması gerekenler
@app.route("/dashboard")
#burada dashboard fonksiyonumuz çalışmadan önce yaptığımız login_required ile giriş yapıp yapmadığımızı belirliyoruz..
@login_required
def dashboard():
    #eğer giriş yapmışsak fonksiyona giriyoruz ve mysql bağlantımızı tamamlıyoruz...
    cursor = mysql.connection.cursor()
    kisiselMakale = "select * from articles where author = %s"

    result = cursor.execute(kisiselMakale,(session["userName"],))
    
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")



#kayıt olma
@app.route('/register', methods=['GET','POST'])
def register():
    form = registerForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        userName = form.userName.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        
        cursor = mysql.connection.cursor()

        ekleme = "insert into users(name,email,userName,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(ekleme,(name,email,userName,password))

        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kayıt oldunuz...","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)



#makale detay sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()

    makaleSorgusu = "select * from articles where id = %s"

    result = cursor.execute(makaleSorgusu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")



#Login işlemi
@app.route("/login", methods = ["GET","POST"])
def login():
    form = loginForm(request.form)
    if request.method == "POST":
        userName = form.userName.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "select * from users where userName = %s"

        result = cursor.execute(sorgu,(userName,))

        if result>0:
            #kullanıcının bütün bilgilerini fetchone ile alıyoruz...
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla giriş yaptınız.","success")
                #giriş yapıldıktan sonra ki işlemimiz
                session["logged_in"] = True
                session["userName"] = userName

                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz.","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı adı yoktur.","danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html", form = form)



#çıkış işlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))



#makale ekle
@app.route("/addarticles", methods = ["GET", "POST"])
def addarticles():
    form = articleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        #makaleyi veri tabanına ekleme
        cursor = mysql.connection.cursor()
        makaleEkle =  "Insert into articles(title, content, author) VALUES(%s,%s,%s)"
        cursor.execute(makaleEkle, (title, content, session["userName"]))
        mysql.connection.commit()

        cursor.close()

        flash("Makaleniz eklendi","success")
        return redirect(url_for("dashboard"))

    return render_template("addarticles.html", form = form)



#makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    silme = "select * from articles where author = %s and id = %s"

    result = cursor.execute(silme,(session["userName"],id))

    if result > 0:
        silme2 = "delete from articles where id = %s"
        cursor.execute(silme2,(id,))
        mysql.connection.commit()
        flash("Makaleyi sildiniz.","danger")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok.","danger")
        return redirect(url_for("index"))



#makale güncelleme işlemi
@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        sorgu = "select * from articles where id = %s and author = %s"

        result = cursor.execute(sorgu,(id,session["userName"]))

        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yoktur.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = articleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html", form = form)
    else:
        #post request kısmımız yani güncelleye bastıktan sonra oluşacak işlemler
        form = articleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        guncellemeSorgusu = "update articles SET title = %s, content = %s where id = %s"

        cursor = mysql.connection.cursor()
        cursor.execute(guncellemeSorgusu,(newTitle,newContent,id))

        mysql.connection.commit()

        flash("Makale başarıyla güncellendi.","success")
        return redirect(url_for("dashboard"))


#makale arama
@app.route("/search", methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("articles"))
    else: 
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "select * from articles,users where articles.author = users.userName and (title like '%" + keyword + "%' or users.userName like '%" + keyword + "%' )"

        result = cursor.execute(sorgu)
        
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı...","warning")
            return redirect(url_for("index"))
        else:
            articles = cursor.fetchall()
            flash("Makaleler getirildi","success")
            return render_template("articles.html",articles = articles)



if __name__ == "__main__":
    app.run(debug=True)
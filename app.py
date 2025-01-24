from flask import Flask, request, session, redirect, url_for, render_template, jsonify
import random
import string


def generate_random_string(length=10):
    characters = string.ascii_letters + string.digits  # 包含大小写字母和数字
    return ''.join(random.choices(characters, k=length))


ADMIN_NAME = 'admin515'

app = Flask(__name__)
app.secret_key = generate_random_string(12)

# 数据存储
users_data = {}  # 保存用户答案和得分
ip_to_user = {}  # IP -> 用户名映射
QUESTIONS = []
with open('questions.txt', 'r') as questions_file:
    for line in questions_file.readlines():
        QUESTIONS.append(line.strip())

last_question_index = 0
current_question_index = 0
answer_open = True


# 工具函数
def get_rankings():
    ranking = sorted(users_data.items(), key=lambda x: x[1].get("total_score", 0), reverse=True)
    return [(user, data["scores"], data["total_score"]) for user, data in ranking]


# 路由
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("quiz"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    global ip_to_user
    client_ip = request.remote_addr

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            return "用户名不能为空", 400

        if client_ip in ip_to_user and ip_to_user[client_ip] != username:
            return f"该IP({client_ip})已经注册为用户 {ip_to_user[client_ip]}，无法重复注册。", 403

        ip_to_user[client_ip] = username
        if username != ADMIN_NAME and username not in users_data:
            users_data[username] = {"answers": {}, "scores": [None] * len(QUESTIONS), "total_score": 0}

        session["username"] = username
        if username != ADMIN_NAME:
            return redirect(url_for("quiz"))
        else:
            return redirect(url_for("admin"))
    return render_template("login.html")


@app.route("/check_score", methods=["GET"])
def check_score():
    if "username" not in session:
        return {"status": "unauthorized"}, 401
    global last_question_index
    username = session["username"]
    current_score = users_data[username].get("scores")[current_question_index]

    if current_score is not None:
        return {"status": "scored", "score": current_score}
    else:
        if last_question_index != current_question_index:
            last_question_index = current_question_index
            return {"status": "scored", "score": current_score}
        return {"status": "pending"}


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    global current_question_index, answer_open

    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    question = QUESTIONS[current_question_index]
    rankings = get_rankings()

    if request.method == "POST":
        answer = request.form.get("answer", "").strip()
        users_data[username]["answers"][current_question_index] = answer
        return render_template("quiz.html", question=question, question_num=current_question_index + 1,
                               rankings=rankings, enumerate=enumerate)

    return render_template("quiz.html", question=question, question_num=current_question_index + 1, rankings=rankings,
                           enumerate=enumerate)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    global current_question_index, answer_open

    if "username" not in session or session["username"] != ADMIN_NAME:
        return "只有管理员可以访问此页面。", 403

    if request.method == "POST":
        # 提交分数
        if "submit_scores" in request.form:
            for user, data in users_data.items():
                if current_question_index in data["answers"]:
                    score = request.form.get(f"{user}_score", 0)
                    try:
                        score = int(score)
                    except ValueError:
                        score = 0
                    data["scores"][current_question_index] = score
                    data["total_score"] = sum([i for i in data["scores"] if i is not None])
            answer_open = False

        # 进入下一题
        elif "next_question" in request.form and current_question_index < len(QUESTIONS) - 1:
            current_question_index += 1
            answer_open = True

        # 返回上一题
        elif "previous_question" in request.form and current_question_index > 0:
            current_question_index -= 1
            answer_open = False  # 保持上一题处于评分状态

    question = QUESTIONS[current_question_index]
    all_answers = {user: data["answers"].get(current_question_index, "") for user, data in users_data.items()}
    rankings = get_rankings()
    return render_template(
        "admin.html",
        question=question,
        question_num=current_question_index + 1,
        all_answers=all_answers,
        answer_open=answer_open,
        current_question_index=current_question_index,
        rankings=rankings,
        enumerate=enumerate
    )


@app.route("/api/check_submissions")
def check_submissions():
    """返回用户提交状态，用于 AJAX 更新"""
    submitted_users = [user for user, data in users_data.items() if current_question_index in data["answers"]]
    return jsonify(submitted_users=submitted_users)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

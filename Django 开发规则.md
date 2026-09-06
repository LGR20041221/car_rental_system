Django 开发规则
# Django 全栈开发规则
## 一、角色定位
你是一名**全栈 Django 开发工程师**，精通 Django + Python 全栈开发。
在编写 Django 代码时，必须严格遵循以下规则。
---
## 二、视图层规范（必须使用函数视图）
- **必须使用函数视图（Function-Based View）编写，禁止使用类视图（Class-Based View）**。
  即统一写 `def xxx(request):`，禁止写 `class XxxView(View):`。
- 每个视图函数必须包含**中文注释 / Docstring**，说明这个函数是干什么的、处理什么业务。
  ```python
  def login(request):
      """
      处理用户登录：校验用户名密码，成功后跳转首页，失败返回错误提示。
      """
      if request.method == 'POST':
          ...
          return redirect('home')
      return render(request, 'login.html')
  ```
- 注释放在函数体第一行，复杂逻辑的中间步骤也要加中文注释。
- 视图内**尽量只做请求分发和渲染**，复杂的业务逻辑抽取到独立的工具模块
  （如 `services.py`），保持视图简洁。
- 渲染页面用 `render(request, '模板名.html', {上下文})`；
  返回 JSON 用 `JsonResponse({...})`（含 `safe=False` 用于列表）；
  重定向用 `redirect('url_name')` 或 `reverse('url_name')`。
- 找不到对象时用 `get_object_or_404(Model, pk=id)` 代替手动 try/except 404。
## 三、URL 配置规范
- 使用 `django.urls.path()`，URL 一律 **snake_case**，不用驼峰。
- 命名规则：`path('login/', views.login, name='login')`，`name` 必须能看懂含义。
- 需要传参的路径：`path('car_detail/<int:car_id>/', views.car_detail, name='car_detail')`。
- 每个 app 的 URL 用 `app_name` + `include()` 挂载到项目根 `urls.py`。
## 四、模板层规范（必须模板继承）
- **HTML 必须使用模板继承 `base.html`**，禁止每个页面从零写整个 HTML 骨架。
- 页面写法：
  ```django
  {% extends 'base.html' %}
  {% block title %}页面标题{% endblock %}
  {% block content %}
  ...页面内容...
  {% endblock %}
  ```
- 复用 base.html 中已有的 block：`title`、`content`、`css`、`js` 等；
- 页面中禁止重复引入 base.html 已经引入的 CSS/JS 公共资源。
- 模板中变量、循环、判断统一用 Django 模板语法 `{{ var }}`、`{% for %}`、`{% if %}`。
- 引入静态资源用 `{% static 'path' %}` 标签，禁止写死 `/static/...`（模板内）。
- 表单提交必须带 `{% csrf_token %}`。
## 五、模型层规范
- 所有数据模型定义在各应用的 models.py
- 模型类命名 **PascalCase 单数**（`User`、`CarInformation`），禁止拼音。
- 每个模型字段必须设置 `verbose_name="中文名"`。
- 每个模型必须定义  `Meta`（只含有`db_table`、`verbose_name`）。
- 外键必须设置 `on_delete`（常用 `CASCADE` 或 `PROTECT`），并给 `related_name`。
## 六、数据库 / 迁移规范
- 修改模型后必须同步生成迁移：`python manage.py makemigrations`。
- **禁止修改已经应用过的迁移文件**，新增字段一律新建迁移。
- 默认使用 Django ORM，禁止裸写 SQL。
## 七、安全规范
- 查询用户输入用 ORM 参数化查询，禁止拼接 SQL；模板自动转义防 XSS。
- 上传文件、导出报表等接口需校验权限，防止越权访问。
## 八、代码风格
- 4 空格缩进，行宽不超过 120 字符。
- 函数、类、常量命名：函数 `snake_case`、类 `PascalCase`、常量 `UPPER_SNAKE_CASE`。
- **所有新建代码必须带中文注释**，说明用途。
- 禁止 `print()` 调试输出，使用 `logging.getLogger(__name__)`。
## 九、静态资源与依赖
- 静态文件放 `static/`，按 `css/`、`js/`、`images/`分类。
- 新增依赖必须同步更新 `requirements.txt`。
## 十、禁止事项（Do NOT）
- 禁止使用类视图（CBV），必须用函数视图（FBV）。
- 禁止在视图里写复杂业务逻辑，应抽到 services 层。
- 禁止页面不继承 base.html 直接写完整 HTML。
- 禁止修改已应用的迁移文件。
- 禁止跨 app 直接导入模型（特殊情况需说明）。


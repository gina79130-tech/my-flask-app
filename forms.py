from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ProductForm(FlaskForm):
    name = StringField('商品名稱', validators=[DataRequired()])
    description = TextAreaField('商品描述', validators=[DataRequired()])
    specifications = TextAreaField('商品規格 (可選)')
    condition = SelectField('新舊程度', choices=[
        ('全新', '全新'),
        ('九成新', '九成新'),
        ('八成新', '八成新'),
        ('有使用痕跡', '有使用痕跡'),
        ('二手', '二手')
    ], validators=[DataRequired()])
    price = FloatField('價格', validators=[DataRequired(), NumberRange(min=0.01)])
    image = FileField('商品圖片', validators=[FileAllowed(['jpg', 'png', 'jpeg'], '僅支援 JPG, PNG, JPEG 格式圖片!')])
    submit = SubmitField('上架商品')

class ShippingAddressForm(FlaskForm):
    recipient_name = StringField('收件人姓名', validators=[DataRequired()])
    phone_number = StringField('聯絡電話', validators=[DataRequired()])
    address_line1 = StringField('地址第一行', validators=[DataRequired()])
    address_line2 = StringField('地址第二行 (可選)')
    city = StringField('城市', validators=[DataRequired()])
    state = StringField('州/省', validators=[DataRequired()])
    zip_code = StringField('郵遞區號', validators=[DataRequired()])
    country = StringField('國家', validators=[DataRequired()])
    submit = SubmitField('儲存地址')

class OrderForm(FlaskForm):
    shipping_method = SelectField('出貨方式', choices=[
        ('郵寄', '郵寄'),
        ('宅配', '宅配'),
        ('超商取貨', '超商取貨')
    ], validators=[DataRequired()])
    submit = SubmitField('確認訂單')
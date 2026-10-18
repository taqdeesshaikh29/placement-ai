from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from app.interview_seed import HR_CATEGORIES, TECHNICAL_CATEGORIES
from app.seed_data import LOGIC, QUANT, VERBAL

LEVELS = ["Easy", "Medium", "Hard"]
APTITUDE_CATEGORIES = [QUANT, LOGIC, VERBAL]
_required = DataRequired(message="This field is required.")


class AptitudeQuestionForm(FlaskForm):
    category = SelectField("Category", choices=[(c, c) for c in APTITUDE_CATEGORIES])
    difficulty = SelectField("Difficulty", choices=[(d, d) for d in LEVELS])
    text = TextAreaField("Question", validators=[_required, Length(max=1000)])
    option_1 = StringField("Option 1", validators=[_required, Length(max=255)])
    option_2 = StringField("Option 2", validators=[_required, Length(max=255)])
    option_3 = StringField("Option 3", validators=[_required, Length(max=255)])
    option_4 = StringField("Option 4", validators=[_required, Length(max=255)])
    correct_option = SelectField("Correct option", coerce=int, choices=[(i, f"Option {i}") for i in range(1, 5)])
    explanation = TextAreaField("Explanation", validators=[_required, Length(max=2000)])
    submit = SubmitField("Save question")

    # fields that change what counts as a correct answer
    ANSWER_FIELDS = ("option_1", "option_2", "option_3", "option_4", "correct_option")


class InterviewQuestionForm(FlaskForm):
    kind = SelectField("Type", choices=[("technical", "Technical"), ("hr", "HR")])
    category = SelectField("Category", choices=[(c, c) for c in TECHNICAL_CATEGORIES + HR_CATEGORIES])
    difficulty = SelectField("Difficulty", choices=[(d, d) for d in LEVELS])
    text = TextAreaField("Question", validators=[_required, Length(max=1000)])
    key_concepts = TextAreaField("Key concepts (one per line)", validators=[_required, Length(max=1000)])
    sample_answer = TextAreaField("Sample answer", validators=[_required, Length(max=3000)])
    submit = SubmitField("Save question")

    def validate_category(self, field):
        allowed = TECHNICAL_CATEGORIES if self.kind.data == "technical" else HR_CATEGORIES
        if field.data not in allowed:
            raise ValidationError("This category does not belong to the selected type.")

    def validate_key_concepts(self, field):
        if "|" in field.data:
            raise ValidationError("Key concepts cannot contain the | character.")
        if not self.concept_list(field.data):
            raise ValidationError("Enter at least one key concept.")

    @staticmethod
    def concept_list(raw):
        return [line.strip() for line in (raw or "").splitlines() if line.strip()]

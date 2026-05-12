import enum


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class EmploymentType(str, enum.Enum):
    permanent = "permanent"
    contract = "contract"
    casual = "casual"
    intern = "intern"


class PayFrequency(str, enum.Enum):
    monthly = "monthly"
    semi_monthly = "semi_monthly"
    weekly = "weekly"
    biweekly = "biweekly"

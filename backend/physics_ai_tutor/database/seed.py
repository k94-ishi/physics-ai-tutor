from physics_ai_tutor.database.database import SessionLocal
from physics_ai_tutor.models.question import Question


def seed():
    db = SessionLocal()
    
    questions = [
        Question(
            question="速度ってなに？",
            answer="だいたい速さと同じですが、速度は向きも含めた量なので、マイナスの値になったり、矢印で表したりします。正確には、速度は「単位時間あたりの位置の変化量」と定義されます。"
        ),
        Question(
            question="加速度ってなに？",
            answer="加速度は、どのくらい加速や減速しているかを表す量で、減速の場合はマイナスの値になります。加速度は矢印で表わされる場合もあり、正確には、「単位時間あたりの速度の変化量」定義されます。"
        ),
    ]
    
    db.add_all(questions)
    db.commit()
    
    db.close()


if __name__ == "__main__":
    seed()
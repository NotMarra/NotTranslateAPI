import asyncio
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Seq2SeqTrainingArguments, Seq2SeqTrainer
from datasets import Dataset
from db import db

async def load_feedback_data():
    collection = db["feedback"]
    cursor = collection.find({"corrected_text": {"$exists": True}})
    data = [
        {"translation": feedback["corrected_text"], "text": feedback["original_text"]}
        async for feedback in cursor
    ]
    return Dataset.from_list(data)

def train_model():
    asyncio.run(_train_model())

async def _train_model():
    dataset = await load_feedback_data()

    model_name = "Helsinki-NLP/opus-mt-en-cs"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    training_args = Seq2SeqTrainingArguments(
        output_dir="./fine_tuned_model",
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        num_train_epochs=3,
        save_total_limit=2
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer
    )

    trainer.train()
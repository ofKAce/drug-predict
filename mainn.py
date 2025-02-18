import streamlit as st
import requests
import matplotlib.pyplot as plt
import base64
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()

# Set API key for Groq
openai.api_base = "https://api.groq.com/openai/v1"
openai.api_key = os.getenv("GROQ_API_KEY")


BASE_URL = "https://www.drugs.com"

def get_drug_url(drug_name):
    processed_name = drug_name.replace(' ', '')
    url = f"{BASE_URL}/alpha/{processed_name[:2]}.html"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        drug_list = soup.select('ul.ddc-list-column-2 li a')
        for drug in drug_list:
            if drug.text.strip().lower().replace('-', '').replace(' ', '') == drug_name.replace('-', '').replace(' ', ''):
                return BASE_URL + drug['href']
    except requests.RequestException as e:
        st.error(f"Error fetching drug page: {e}")
    return None

def get_additional_links(drug_url):
    try:
        response = requests.get(drug_url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        more_resources = soup.find('div', class_='more-resources')
        reviews_link, side_effects_link = "Not Found", "Not Found"
        if more_resources:
            for a in more_resources.find_all('a', href=True):
                if "reviews" in a.text.lower():
                    reviews_link = BASE_URL + a['href']
                elif "side effects" in a.text.lower():
                    side_effects_link = BASE_URL + a['href']
        return reviews_link, side_effects_link
    except requests.RequestException as e:
        st.error(f"Error fetching additional links: {e}")
    return None, None

def extract_sentiment_with_ai(review_text):
    try:
        response = openai.ChatCompletion.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "Predict whether the review is Positive or Negative."},
                {"role": "user", "content": review_text}
            ]
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        st.error(f"Error analyzing sentiment: {e}")
        return "unknown"

def scrape_reviews(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        review_divs = soup.find_all('div', class_='ddc-comment ddc-box ddc-mgb-2')
        positive_count, negative_count = 0, 0
        for div in review_divs:
            review_text = div.get_text(strip=True, separator=" ")
            sentiment = extract_sentiment_with_ai(review_text)
            if "positive" in sentiment:
                positive_count += 1
            elif "negative" in sentiment:
                negative_count += 1
        return positive_count, negative_count
    except Exception as e:
        st.error(f"Error scraping reviews: {e}")
        return 0, 0

def scrape_side_effects(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        accordion_divs = soup.find_all('div', class_='ddc-accordion-content')
        return "\n".join(div.get_text(strip=True, separator=" ") for div in accordion_divs)
    except requests.RequestException as e:
        st.error(f"Error fetching side effects: {e}")
        return ""

def extract_sideEffect(sideEffect_text):
    if not sideEffect_text.strip():
        return "No valid side-effect text found."
    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "The given text describes side effects of a medical drug. Provide a summary."},
                {"role": "user", "content": sideEffect_text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error summarizing side effects: {e}")
        return "Error generating summary."

def plot_sentiment_chart(positive, negative):
    labels = ['Positive', 'Negative']
    counts = [positive, negative]
    colors = ['#4CAF50', '#FF5733']
    plt.figure(figsize=(6, 6))
    plt.pie(counts, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    plt.title('Sentiment Analysis')
    st.pyplot(plt)

def main():
    st.title("Drug Review Sentiment Analyzer")
    drug_name = st.text_input("Enter Drug Name:").lower().strip().replace(' ','')
    if st.button("Analyze"):
        with st.spinner("Fetching drug details..."):
            drug_url = get_drug_url(drug_name)
            if not drug_url:
                st.error("Drug not found on Drugs.com.")
                return
            reviews_link, side_effects_link = get_additional_links(drug_url)
        
        with st.spinner("Analyzing reviews..."):
            positive, negative = scrape_reviews(reviews_link) if reviews_link != "Not Found" else (0, 0)
        
        with st.spinner("Fetching and summarizing side effects..."):
            raw_side_effects = scrape_side_effects(side_effects_link) if side_effects_link != "Not Found" else "No side effects found."
            summarized_side_effects = extract_sideEffect(raw_side_effects)
        
        st.subheader("Sentiment Analysis")
        plot_sentiment_chart(positive, negative)
        
        st.subheader("Side Effects Summary")
        st.text_area("", summarized_side_effects, height=200)

if __name__ == "__main__":
    main()

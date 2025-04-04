import os
import json
import logging
import google.generativeai as genai
from flask import current_app
import requests

# Configure logging
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.provider = "gemini"  # Default to Gemini
        self.gemini_api_key = current_app.config.get("GEMINI_API_KEY", "")
        self.groq_api_key = current_app.config.get("GROQ_API_KEY", "")
        
        # Debug information
        logger.debug(f"Gemini API Key available: {bool(self.gemini_api_key)}")
        logger.debug(f"Groq API Key available: {bool(self.groq_api_key)}")
        
        # Initialize Gemini if API key exists
        if self.gemini_api_key:
            logger.info("Using Gemini API for AI services")
            genai.configure(api_key=self.gemini_api_key)
        else:
            # Fallback to Groq if Gemini key is not available but Groq is
            if self.groq_api_key:
                logger.info("Using Groq API for AI services")
                self.provider = "groq"
            else:
                logger.warning("No API keys found for Gemini or Groq. AI services will not function.")
    
    def _get_gemini_response(self, prompt):
        """Get response from Gemini API"""
        try:
            # Using the latest Gemini 1.5 Pro model
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # If the above fails, try with the Gemini 1.0 Pro model
            try:
                model = genai.GenerativeModel('gemini-1.0-pro')
                response = model.generate_content(prompt)
                return response.text
            except Exception as e2:
                logger.error(f"Error with Gemini API: {str(e2)}")
                return f"Error generating response: {str(e2)}"
    
    def _get_groq_response(self, prompt):
        """Get response from Groq API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama3-8b-8192",  # Using Llama 3 8B model
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1024
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"Groq API error: {response.status_code}, {response.text}")
                return f"Error: {response.status_code}, {response.text}"
        except Exception as e:
            logger.error(f"Error with Groq API: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def get_response(self, prompt):
        """Get AI response based on available provider"""
        if self.provider == "gemini" and self.gemini_api_key:
            return self._get_gemini_response(prompt)
        elif self.provider == "groq" and self.groq_api_key:
            return self._get_groq_response(prompt)
        else:
            return "No API key configured for AI services."
    
    def generate_email(self, context, preferences=None):
        """Generate an email draft based on context and user preferences"""
        pref_text = ""
        if preferences:
            pref_text = f"""
            Tone: {preferences.email_tone}
            Length: {preferences.email_length}
            """
        
        prompt = f"""
        Generate a professional email with the following details:
        {context}
        
        User preferences:
        {pref_text}
        
        Format the response with a subject line and email body.
        """
        
        response = self.get_response(prompt)
        
        # Try to extract subject from response
        subject = "No Subject"
        body = response
        
        # Look for common subject line formats in the response
        if "Subject:" in response:
            parts = response.split("Subject:", 1)
            if len(parts) > 1:
                subject_part = parts[1].strip()
                if "\n" in subject_part:
                    subject = subject_part.split("\n", 1)[0].strip()
                    body = parts[1].split("\n", 1)[1].strip() if len(parts[1].split("\n", 1)) > 1 else ""
                else:
                    subject = subject_part
                    body = ""
        
        return {
            "subject": subject,
            "body": body
        }
    
    def generate_report(self, context, report_type, preferences=None):
        """Generate a business report based on context and type"""
        pref_text = ""
        if preferences:
            pref_text = f"""
            Format: {preferences.report_format}
            Tone: {preferences.report_tone}
            """
        
        prompt = f"""
        Generate a {report_type} business report based on the following information:
        {context}
        
        User preferences:
        {pref_text}
        
        Format the report with a title, executive summary, detailed sections, and conclusion.
        """
        
        response = self.get_response(prompt)
        
        # Try to extract title from response
        title = f"{report_type.capitalize()} Report"
        content = response
        
        # Look for common title formats in the response
        if "Title:" in response:
            parts = response.split("Title:", 1)
            if len(parts) > 1:
                title_part = parts[1].strip()
                if "\n" in title_part:
                    title = title_part.split("\n", 1)[0].strip()
                    content = parts[1].split("\n", 1)[1].strip() if len(parts[1].split("\n", 1)) > 1 else ""
                else:
                    title = title_part
                    content = ""
        elif "# " in response:  # Markdown title format
            parts = response.split("# ", 1)
            if len(parts) > 1:
                title_part = parts[1].strip()
                if "\n" in title_part:
                    title = title_part.split("\n", 1)[0].strip()
                    content = "# " + title + "\n" + parts[1].split("\n", 1)[1].strip() if len(parts[1].split("\n", 1)) > 1 else ""
                else:
                    title = title_part
                    content = "# " + title
        
        return {
            "title": title,
            "content": content
        }
    
    def chatbot_response(self, message, chat_history=None, preferences=None):
        """Generate a chatbot response based on message and chat history"""
        if chat_history is None:
            chat_history = []
        
        history_text = ""
        for msg in chat_history[-5:]:  # Include up to 5 recent messages for context
            sender = "User" if msg.get("is_user", True) else "Assistant"
            history_text += f"{sender}: {msg.get('content', '')}\n"
        
        pref_text = ""
        if preferences:
            pref_text = f"Tone: {preferences.chat_tone}"
        
        prompt = f"""
        You are a business communication assistant chatbot. Respond to the following message:
        
        Chat history:
        {history_text}
        
        User message: {message}
        
        User preferences:
        {pref_text}
        
        Provide a helpful, concise, and relevant response.
        """
        
        return self.get_response(prompt)

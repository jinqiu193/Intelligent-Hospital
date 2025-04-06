
# AI Medical Triage System

An intelligent medical triage system based on Flask and Moonshot AI that collects patient information through multi-turn dialogues, providing preliminary diagnostic suggestions and medical guidance.

## Features

- 🤖 Intelligent Medical Consultation: Progressive understanding of patient symptoms through multi-turn dialogues
- 🎙️ Voice Input Support: Support voice description of symptoms
- 📝 Professional Medical Records: Automatically generate standardized outpatient medical records
- 🏥 Department Recommendation: Smart recommendation of medical departments based on symptoms
- 🔒 Privacy Protection: Ensure patient information security
- 📱 Responsive Interface: Support access from various devices

## Tech Stack

- Backend: Flask
- AI Model: Moonshot AI
- Frontend: HTML5 + CSS3 + JavaScript
- Voice Recognition: SpeechRecognition
- UI Components: Font Awesome
- Markdown Rendering: Marked.js

## Quick Start

### Requirements

- Python 3.7+
- Flask
- OpenAI Python SDK
- SpeechRecognition

### Installation

```bash
pip install flask openai speechrecognition
```

### Configuration

1. Set up Moonshot AI API key in the code:

```python
client = OpenAI(
    base_url="https://api.moonshot.cn/v1",
    api_key="your-api-key"
)
```

### Running

```bash
python app.py
```

Access the system at `http://localhost:5000`.

## Usage Flow

1. Fill in basic information: gender, age, occupation, marital status
2. Describe main symptoms (text or voice input supported)
3. Answer follow-up questions for detailed information
4. Receive diagnostic suggestions and medical guidance

## System Features

### Intelligent Consultation

- Dynamic questioning strategy
- Professional medical knowledge support
- Timely warning for critical symptoms

### Medical Records

Automatically generates standardized medical records including:
- Chief Complaint
- Present Illness History
- Past Medical History
- Preliminary Diagnosis
- Medical Advice

### User Interface

- Dark theme design
- Smooth animations
- Intuitive operation

## Important Notes

- This system's suggestions are for reference only and cannot replace professional medical diagnosis
- Seek immediate medical attention in case of emergency
- Please provide accurate symptom information

## License

MIT License

## Contributing

Issues and Pull Requests are welcome to help improve the project.

## Acknowledgments

- [Moonshot AI](https://www.moonshot.cn/) - AI model support
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Font Awesome](https://fontawesome.com/) - Icon support
- [Marked.js](https://marked.js.org/) - Markdown rendering


## API Documentation

### Endpoints

#### POST /submit
Process user input and return AI response

**Request Body:**
- `text_input`: Text message from user
- `audio_input`: Audio file for voice input

**Response:**
```json
{
    "result": "AI response message"
}
```

## Development

### Local Development

1. Clone the repository
2. Install dependencies
3. Set up environment variables
4. Run the development server

### Testing

Run tests using:
```bash
python -m pytest
```

### Deployment

The application can be deployed using Docker or traditional hosting services.

## Security

- All patient data is processed locally
- No permanent storage of consultation data
- Secure API communication

## Future Enhancements

- Multi-language support
- Integration with electronic health records
- Advanced symptom analysis
- Real-time doctor consultation
- Mobile application development

## Support

For support, please open an issue in the repository or contact the development team.

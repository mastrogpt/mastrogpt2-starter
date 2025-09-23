import json
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field

# ============================================================================
# Constants and Enums
# ============================================================================

class DemoCommand(Enum):
    """Available demo commands"""
    CODE = "code"
    CHESS = "chess"
    HTML = "html"
    FORM = "form"
    MESSAGE = "message"
    OPTIONS = "options"
    QUEST = "quest"

class StyleType(Enum):
    """Main style types for questionnaire"""
    CLASSICO = "Classico"
    ELEGANTE = "Elegante"
    ROMANTICO = "Romantico"
    SEDUCENTE = "Seducente"
    NATURALE_SPORTIVO = "Naturale-sportivo"
    FASHIONISTA_DRAMMATICO = "Fashionista-drammatico"
    CREATIVO = "Creativo"

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FormField:
    """Represents a form field"""
    name: str
    label: str
    type: str
    required: str = "true"
    options: Optional[List[Union[str, Dict[str, str]]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        result = {
            "name": self.name,
            "label": self.label,
            "type": self.type,
            "required": self.required
        }
        if self.options:
            result["options"] = self.options
        return result

@dataclass
class QuestionnaireConfig:
    """Configuration for the style questionnaire"""
    main_styles: List[str] = field(default_factory=list)
    substyles: Dict[str, List[str]] = field(default_factory=dict)
    color_models: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.main_styles = [style.value for style in StyleType]
        self.substyles = {
            StyleType.CLASSICO.value: ["Dandy", "Navy", "Preppy", "Minimal"],
            StyleType.ROMANTICO.value: ["bon ton", "lolita"],
            StyleType.SEDUCENTE.value: ["pin-up"],
            StyleType.NATURALE_SPORTIVO.value: ["Hip Hop", "Rap", "Skater"],
            StyleType.CREATIVO.value: [
                "vintage", "maximalist", "nerd-hipster", "metal", "punk", 
                "emo", "gotico", "grunge", "rock", "hippie", "boho", 
                "country", "etnico", "animalier", "indie", "tribal"
            ]
        }
        self.color_models = ["HSB", "HSL"]

# ============================================================================
# Sample Content
# ============================================================================

class DemoContent:
    """Container for demo content"""
    
    USAGE = "Please type one of 'code', 'chess', 'html', 'form', 'message', 'options', 'quest' or 'images:a,b,c' with a,b,c in s3"
    
    SAMPLE_FORM = [
        FormField(
            name="why",
            label="Why do you recommend Apache OpenServerless?",
            type="textarea",
            required="true"
        ),
        FormField(
            name="job",
            label="What is your job role?",
            type="text",
            required="true"
        ),
        FormField(
            name="tone",
            label="What tone should the post have?",
            type="text",
            required="true"
        )
    ]
    
    HTML_SAMPLE = """<div class="max-w-md mx-auto p-6 bg-white shadow-md rounded-lg">
  <h1 class="text-2xl font-bold text-gray-800 mb-6">Sample Form</h1>
  <form action="/submit-your-form-endpoint" method="post" class="space-y-4">
    <div class="flex flex-col">
      <label for="username" class="mb-2 text-sm font-medium text-gray-700">Username:</label>
      <input
        type="text"
        id="username"
        name="username"
        required
        class="p-2 border border-gray-300 rounded-md bg-white text-black focus:ring-2 focus:ring-teal-500 focus:outline-none"
      />
    </div>
    <div class="flex flex-col">
      <label for="password" class="mb-2 text-sm font-medium text-gray-700">Password:</label>
      <input
        type="password"
        id="password"
        name="password"
        required
        class="p-2 border border-gray-300 rounded-md bg-white text-black focus:ring-2 focus:ring-teal-500 focus:outline-none"
      />
    </div>
    <div>
      <button
        type="submit"
        class="w-full py-2 bg-blue-500 text-white font-semibold rounded-md hover:bg-blue-600 focus:ring-2 focus:ring-blue-400 focus:outline-none"
      >
        Login
      </button>
    </div>
  </form>
</div>"""
    
    PYTHON_CODE = """def sum_to(n):
    \"\"\"Calculate sum of numbers from 1 to n\"\"\"
    return sum(range(1, n + 1))"""
    
    CHESS_POSITION = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2"

# ============================================================================
# Questionnaire Manager
# ============================================================================

class QuestionnaireManager:
    """Manages the style questionnaire flow"""
    
    def __init__(self):
        self.config = QuestionnaireConfig()
    
    def get_complete_form(self) -> List[Dict[str, Any]]:
        """Get the complete questionnaire form"""
        fields = [
            FormField(
                name="main_style",
                label="Seleziona il tuo stile principale",
                type="radio",
                options=self.config.main_styles,
                required="true"
            )
        ]
        
        # Add substyle fields
        for main_style, substyles in self.config.substyles.items():
            fields.append(FormField(
                name=f"{main_style.lower().replace('-', '_')}_substyle",
                label=f"Sottostili {main_style} (solo se hai scelto {main_style})",
                type="radio",
                options=substyles,
                required="false"
            ))
        
        # Add color and preference fields
        additional_fields = [
            FormField("color_model", "Modello colore", "radio", "true", self.config.color_models),
            FormField("hue", "Hue (temperatura)", "radio", "true", ["warm", "cool"]),
            FormField("saturation", "Saturation (intensità)", "radio", "true", ["high", "low"]),
            FormField("brightness", "Brightness (luminosità)", "radio", "true", ["light", "dark"]),
            FormField("color_picker", "Hai usato il color picker?", "radio", "true", ["Si", "No"]),
            FormField("seasonal_colors", "Conosci la tua stagione armocromatica?", "radio", "true", ["Si", "No"]),
            FormField("season", "Stagione presente (solo se conosci la tua stagione)", "radio", "false", 
                     ["Spring", "Summer", "Autumn", "Winter", "Suspect of Winter"]),
            FormField("main_needs", "Necessità principali", "radio", "true",
                     ["Daily work", "Business meeting", "Free time during the day", 
                      "evening outings", "Home stay", "Date", "Hiking", "Work out", "courses/activities"]),
            FormField("favorite_colors", "Colori che indossi più spesso", "radio", "true",
                     ["bianco", "nero", "rosso", "giallo", "blu", "verde", "viola", 
                      "arancione", "rosa", "grigio"])
        ]
        
        fields.extend(additional_fields)
        return [field.to_dict() for field in fields]
    
    def generate_recommendations(self, user_data: Dict[str, Any]) -> str:
        """Generate personalized style recommendations"""
        recommendations = ["## I tuoi risultati di stile personalizzati\n"]
        
        main_style = user_data.get("main_style", "Non specificato")
        
        # Add main style and substyle
        substyle_key = f"{main_style.lower().replace('-', '_')}_substyle"
        substyle = user_data.get(substyle_key, "")
        
        if substyle:
            recommendations.append(f"**Stile principale:** {main_style} - {substyle}")
        else:
            recommendations.append(f"**Stile principale:** {main_style}")
        
        # Add color palette recommendations
        self._add_color_recommendations(recommendations, user_data)
        
        # Add occasion and preferences
        main_needs = user_data.get("main_needs", "")
        if main_needs:
            recommendations.append(f"\n**Occasioni principali:** {main_needs}")
        
        favorite_colors = user_data.get("favorite_colors", "")
        if favorite_colors:
            recommendations.append(f"\n**Colore preferito:** {favorite_colors}")
        
        # Add style-specific tips
        self._add_style_tips(recommendations, main_style)
        
        return "\n".join(recommendations)
    
    def _add_color_recommendations(self, recommendations: List[str], user_data: Dict[str, Any]):
        """Add color palette recommendations"""
        recommendations.append(f"\n**Palette colori consigliata:**")
        
        color_fields = ["color_model", "hue", "saturation", "brightness"]
        field_labels = {
            "color_model": "Modello",
            "hue": "Temperatura",
            "saturation": "Intensità",
            "brightness": "Luminosità"
        }
        
        for field in color_fields:
            value = user_data.get(field, "")
            if value:
                recommendations.append(f"- {field_labels[field]}: {value}")
        
        if user_data.get("seasonal_colors") == "Si":
            season = user_data.get("season", "")
            if season:
                recommendations.append(f"- Stagione armocromatica: {season}")
        
        color_picker = user_data.get("color_picker", "")
        if color_picker:
            recommendations.append(f"- Uso color picker: {color_picker}")
    
    def _add_style_tips(self, recommendations: List[str], main_style: str):
        """Add style-specific tips"""
        style_tips = {
            StyleType.CLASSICO.value: [
                "Punta su capi senza tempo e di qualità",
                "Privilegia linee pulite e tagli perfetti",
                "Investi in accessori di buona fattura"
            ],
            StyleType.CREATIVO.value: [
                "Sperimenta con texture e pattern inusuali",
                "Non aver paura di mixare stili diversi",
                "Usa gli accessori come statement pieces"
            ],
            StyleType.ROMANTICO.value: [
                "Scegli tessuti morbidi e fluidi",
                "Privilegia dettagli delicati come pizzi e ricami",
                "Opta per silhouette femminili e avvolgenti"
            ],
            StyleType.ELEGANTE.value: [
                "Investi in capi di alta qualità e taglio impeccabile",
                "Mantieni una palette neutra e sofisticata",
                "Accessori minimal ma di pregio"
            ],
            StyleType.SEDUCENTE.value: [
                "Enfatizza le tue curve con tagli aderenti",
                "Gioca con trasparenze e scollature strategiche",
                "Usa colori intensi e materiali lucidi"
            ],
            StyleType.NATURALE_SPORTIVO.value: [
                "Privilegia comfort e praticità",
                "Scegli tessuti tecnici e traspiranti",
                "Accessori funzionali e sportivi"
            ],
            StyleType.FASHIONISTA_DRAMMATICO.value: [
                "Osa con capi statement e trend del momento",
                "Mixa pattern e texture audaci",
                "Accessori vistosi e di carattere"
            ]
        }
        
        tips = style_tips.get(main_style, [])
        if tips:
            recommendations.append("\n**Consigli per il tuo stile:**")
            for tip in tips:
                recommendations.append(f"- {tip}")

# ============================================================================
# Main Demo Handler
# ============================================================================

class DemoHandler:
    """Main handler for demo application"""
    
    def __init__(self):
        self.questionnaire_manager = QuestionnaireManager()
        self.content = DemoContent()
    
    def handle_request(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming request"""
        # Initialize or update state
        state = self._initialize_state(args)
        
        # Get input
        input_value = args.get("input", "")
        
        # Process request
        if isinstance(input_value, dict) and "form" in input_value:
            return self._handle_form_submission(input_value["form"], state)
        else:
            return self._handle_command(input_value, state)
    
    def _initialize_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize or update state"""
        try:
            state = json.loads(args.get("state", "{}"))
            if not state:
                state = {"counter": 1}
            else:
                state["counter"] = state.get("counter", 0) + 1
        except:
            state = {"counter": 1}
        return state
    
    def _handle_form_submission(self, form_data: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle form submission"""
        if state.get("questionnaire_step") == "complete_form":
            # Store questionnaire responses
            for key, value in form_data.items():
                if value:
                    state[key] = value
            
            state["questionnaire_step"] = "completed"
            
            # Generate recommendations
            recommendations = self.questionnaire_manager.generate_recommendations(state)
            
            # Return both the recommendations and the options
            return {
                "output": recommendations,  # The actual recommendations text
                "options": json.dumps({"options": ["Start new questionnaire", "Back to main menu"]}),
                "state": json.dumps(state)
            }
        else:
            # Regular form submission
            output = "FORM:\n"
            for field, value in form_data.items():
                output += f"{field}: {value}\n"
            
            return {"output": output, "state": json.dumps(state)}
    
    def _handle_command(self, command: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle command input"""
        response = {"state": json.dumps(state)}
        
        if command == "":
            response["output"] = f"Welcome to the Demo chat. {self.content.USAGE}"
        
        elif command == DemoCommand.CODE.value:
            response.update({
                "output": f"Here is some python code.\n```python\n{self.content.PYTHON_CODE}\n```",
                "code": self.content.PYTHON_CODE,
                "language": "python"
            })
        
        elif command == DemoCommand.HTML.value:
            response.update({
                "output": f"Here is some HTML.\n```html\n{self.content.HTML_SAMPLE}\n```",
                "html": self.content.HTML_SAMPLE
            })
        
        elif command == DemoCommand.MESSAGE.value:
            response.update({
                "output": "Here is a sample message.",
                "message": "This is the message.",
                "title": "This is the title"
            })
        
        elif command == DemoCommand.FORM.value:
            response.update({
                "output": "Please fill the form",
                "form": [field.to_dict() for field in self.content.SAMPLE_FORM]
            })
        
        elif command == DemoCommand.CHESS.value:
            response.update({
                "output": f"Check this chess position.\n\n{self.content.CHESS_POSITION}",
                "chess": self.content.CHESS_POSITION
            })
        
        elif command == DemoCommand.OPTIONS.value:
            response["output"] = json.dumps({"options": ["who are you", "what can you do"]})
        
        elif command == DemoCommand.QUEST.value:
            state["questionnaire_step"] = "complete_form"
            response.update({
                "output": "**Questionario di Stile Personale**\n\nCompila tutte le sezioni del questionario sottostante per scoprire il tuo stile personale. Le sezioni dei sottostili sono opzionali - compila solo quella corrispondente al tuo stile principale.",
                "form": self.questionnaire_manager.get_complete_form(),
                "state": json.dumps(state)
            })
        
        elif command == "Start new questionnaire":
            state = {"counter": state["counter"], "questionnaire_step": "complete_form"}
            response.update({
                "output": "**Nuovo Questionario di Stile Personale**\n\nCompila tutte le sezioni del questionario sottostante per scoprire il tuo stile personale. Le sezioni dei sottostili sono opzionali - compila solo quella corrispondente al tuo stile principale.",
                "form": self.questionnaire_manager.get_complete_form(),
                "state": json.dumps(state)
            })
        
        elif command == "Back to main menu":
            state = {"counter": state["counter"]}
            response.update({
                "output": f"Tornato al menu principale. {self.content.USAGE}",
                "state": json.dumps(state)
            })
        
        elif command == "who are you":
            response["output"] = "I am a demo bot that can show you different types of content. I can display code, chess positions, HTML forms, and messages. Try typing 'options' to see what I can do!"
        
        elif command == "what can you do":
            response["output"] = (
                "I can show you various types of content:\n"
                "- 'code': Display Python code examples\n"
                "- 'chess': Show chess positions\n"
                "- 'html': Display HTML forms\n"
                "- 'form': Show interactive forms\n"
                "- 'message': Display sample messages\n"
                "- 'options': Show option buttons\n"
                "- 'quest': Personal style questionnaire with radio buttons\n\n"
                f"{self.content.USAGE}"
            )

        elif command.startswith("images:"):
            response["output"] = "Displaying images from S3."
            response["images"] = command[7:]  # Extract images part
        
        else:
            response["output"] = f"You made {state['counter']} requests. {self.content.USAGE}"
        
        return response

# ============================================================================
# Main Entry Point
# ============================================================================

def demo(args: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for the demo application"""
    handler = DemoHandler()
    result = handler.handle_request(args)
    
    # Ensure the result has the correct structure
    # The original code expects specific fields like 'output', 'state', 'form', etc.
    final_result = {}
    
    # Always include output if present
    if "output" in result:
        final_result["output"] = result["output"]
    
    # Include answer if present (for questionnaire results)
    if "answer" in result:
        final_result["answer"] = result["answer"]
    
    # Include state if present
    if "state" in result:
        final_result["state"] = result["state"]
    
    # Include form fields if present
    if "form" in result:
        final_result["form"] = result["form"]

    # Include form fields if present
    if "images" in result:
        final_result["images"] = result["images"]


    # Include other fields from the original structure
    for key in ["language", "message", "title", "chess", "code", "html"]:
        if key in result:
            final_result[key] = result[key]
    
    return final_result
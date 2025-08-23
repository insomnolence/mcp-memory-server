"""
Question definitions and flow for the configuration wizard.

This module defines the question structure, flow, and human-friendly options
that will be mapped to technical configuration parameters.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class QuestionType(Enum):
    """Types of questions supported by the wizard."""
    CHOICE = "choice"           # Single choice from options
    MULTIPLE_CHOICE = "multiple_choice"  # Multiple selections
    NUMERIC = "numeric"         # Numeric input with validation
    TEXT = "text"              # Free text input
    BOOLEAN = "boolean"        # Yes/No question


@dataclass
class QuestionOption:
    """Represents a single option in a choice question."""
    key: str                   # Technical identifier
    display: str              # Human-readable description
    help_text: str            # Additional explanation
    recommended: bool = False  # Whether this is the recommended option


@dataclass
class Question:
    """Represents a single configuration question."""
    id: str                           # Unique question identifier
    title: str                        # Question title/prompt
    description: str                  # Detailed explanation
    question_type: QuestionType       # Type of question
    options: Optional[List[QuestionOption]] = None  # For choice questions
    default: Optional[Any] = None     # Default value
    required: bool = True            # Whether answer is required
    depends_on: Optional[str] = None # Previous question this depends on
    depends_value: Optional[Any] = None  # Required value of dependency
    validation: Optional[Dict[str, Any]] = None  # Validation rules
    impact_explanation: Optional[str] = None     # What this affects


class QuestionFlow:
    """Defines the complete question flow for configuration."""
    
    def __init__(self):
        self.questions = self._define_questions()
        self.question_map = {q.id: q for q in self.questions}
    
    def _define_questions(self) -> List[Question]:
        """Define all configuration questions in logical order."""
        
        questions = [
            # 1. Use Case & Purpose
            Question(
                id="use_case",
                title="What's your primary use case?",
                description="This helps us optimize default settings for your specific needs.",
                question_type=QuestionType.CHOICE,
                options=[
                    QuestionOption(
                        key="development",
                        display="Software Development",
                        help_text="Code snippets, debugging sessions, architecture decisions",
                        recommended=True
                    ),
                    QuestionOption(
                        key="research",
                        display="Research & Analysis",
                        help_text="Papers, findings, experimental results, data analysis"
                    ),
                    QuestionOption(
                        key="creative",
                        display="Creative Work",
                        help_text="Writing projects, brainstorming sessions, creative iterations"
                    ),
                    QuestionOption(
                        key="business",
                        display="Business Operations",
                        help_text="Meeting notes, decisions, processes, customer interactions"
                    ),
                    QuestionOption(
                        key="general",
                        display="General Purpose",
                        help_text="Mixed use case, balanced settings"
                    )
                ]
            ),
            
            # 2. Memory Retention Strategy
            Question(
                id="retention_strategy",
                title="How long should memories typically last?",
                description="This determines the base time-to-live (TTL) settings for different types of content.",
                question_type=QuestionType.CHOICE,
                options=[
                    QuestionOption(
                        key="session_based",
                        display="During my work session (hours)",
                        help_text="Good for temporary context, clears frequently"
                    ),
                    QuestionOption(
                        key="daily",
                        display="A few days",
                        help_text="Balances freshness with persistence"
                    ),
                    QuestionOption(
                        key="weekly",
                        display="About a week",
                        help_text="Good for project-based work",
                        recommended=True
                    ),
                    QuestionOption(
                        key="monthly",
                        display="Several weeks to months",
                        help_text="Long-term knowledge retention"
                    ),
                    QuestionOption(
                        key="permanent",
                        display="Until I explicitly delete",
                        help_text="Maximum retention, manual cleanup required"
                    )
                ]
            ),
            
            # 3. Content Importance Factors
            Question(
                id="importance_factors",
                title="What makes content important to remember?",
                description="This configures the scoring weights that determine which memories are kept longer.",
                question_type=QuestionType.CHOICE,
                options=[
                    QuestionOption(
                        key="recency_focused",
                        display="Recent activity matters most",
                        help_text="Prioritizes new information and recent interactions"
                    ),
                    QuestionOption(
                        key="relevance_focused", 
                        display="Content relevance is key",
                        help_text="Prioritizes semantic similarity and topical relevance",
                        recommended=True
                    ),
                    QuestionOption(
                        key="frequency_focused",
                        display="How often I access it",
                        help_text="Prioritizes frequently referenced content"
                    ),
                    QuestionOption(
                        key="balanced",
                        display="Balanced approach",
                        help_text="Equal weighting of all factors"
                    )
                ]
            ),
            
            # 4. Storage and Performance
            Question(
                id="storage_preference",
                title="How much storage can you dedicate to memory?",
                description="This affects collection sizes and cleanup frequency.",
                question_type=QuestionType.CHOICE,
                options=[
                    QuestionOption(
                        key="minimal",
                        display="Minimal (fast cleanup)",
                        help_text="50 short-term, aggressive cleanup - good for limited resources"
                    ),
                    QuestionOption(
                        key="standard",
                        display="Standard (balanced)",
                        help_text="100 short-term, regular cleanup - good balance",
                        recommended=True
                    ),
                    QuestionOption(
                        key="large",
                        display="Large (more retention)",
                        help_text="200+ short-term, less frequent cleanup"
                    ),
                    QuestionOption(
                        key="unlimited",
                        display="Maximum retention",
                        help_text="Large collections, minimal cleanup"
                    )
                ]
            ),
            
            # 5. Content Types Priority
            Question(
                id="content_priorities",
                title="Which content types are most valuable?",
                description="This adjusts scoring bonuses for different content patterns.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=[
                    QuestionOption(
                        key="code",
                        display="Code snippets and programming content",
                        help_text="Functions, classes, bug fixes, solutions"
                    ),
                    QuestionOption(
                        key="errors",
                        display="Error messages and debugging info",
                        help_text="Stack traces, error logs, troubleshooting"
                    ),
                    QuestionOption(
                        key="architecture",
                        display="Architecture and design decisions",
                        help_text="System design, patterns, structural decisions"
                    ),
                    QuestionOption(
                        key="critical",
                        display="Critical or urgent information",
                        help_text="Important notices, breaking changes, urgent items"
                    ),
                    QuestionOption(
                        key="documentation",
                        display="Documentation and explanations",
                        help_text="How-to guides, explanations, documentation"
                    )
                ]
            ),
            
            # 6. Performance vs Accuracy Trade-off
            Question(
                id="performance_preference",
                title="Performance vs. Memory Accuracy preference?",
                description="This affects maintenance intervals and processing frequency.",
                question_type=QuestionType.CHOICE,
                options=[
                    QuestionOption(
                        key="performance",
                        display="Favor performance",
                        help_text="Less frequent maintenance, faster responses"
                    ),
                    QuestionOption(
                        key="balanced",
                        display="Balanced",
                        help_text="Regular maintenance, good balance",
                        recommended=True
                    ),
                    QuestionOption(
                        key="accuracy",
                        display="Favor accuracy",
                        help_text="Frequent maintenance, most accurate results"
                    )
                ]
            ),
            
            # 7. Template Selection (Optional Quick Setup)
            Question(
                id="use_template",
                title="Would you like to use a pre-built template?",
                description="Templates provide optimized settings for common use cases and can save time.",
                question_type=QuestionType.BOOLEAN,
                default=False,
                required=False,
                impact_explanation="Templates provide quick setup but custom configuration offers more control"
            ),
            
            # 8. Template Selection
            Question(
                id="template_choice",
                title="Choose a configuration template:",
                description="Each template is optimized for specific workflows and usage patterns.",
                question_type=QuestionType.CHOICE,
                depends_on="use_template",
                depends_value=True,
                options=[
                    QuestionOption(
                        key="development",
                        display="Software Development",
                        help_text="Optimized for code, debugging, and architecture work",
                        recommended=True
                    ),
                    QuestionOption(
                        key="research",
                        display="Research & Analysis", 
                        help_text="Extended retention for research findings and documentation"
                    ),
                    QuestionOption(
                        key="creative",
                        display="Creative Work",
                        help_text="Balanced for writing, brainstorming, and creative projects"
                    ),
                    QuestionOption(
                        key="business",
                        display="Business Operations",
                        help_text="Optimized for meetings, processes, and customer interactions"
                    ),
                    QuestionOption(
                        key="minimal",
                        display="Minimal Resources",
                        help_text="Fast cleanup, low storage usage"
                    ),
                    QuestionOption(
                        key="maximum",
                        display="Maximum Retention",
                        help_text="Extensive storage, minimal cleanup"
                    )
                ]
            ),
            
            # 9. Server Configuration
            Question(
                id="server_accessibility",
                title="How will you access the memory server?",
                description="This determines the server host binding and accessibility.",
                question_type=QuestionType.CHOICE,
                depends_on="use_template",
                depends_value=False,
                options=[
                    QuestionOption(
                        key="localhost",
                        display="Only from this machine (localhost)",
                        help_text="Server binds to 127.0.0.1 - most secure, local access only",
                        recommended=True
                    ),
                    QuestionOption(
                        key="network",
                        display="From other machines on network",
                        help_text="Server binds to 0.0.0.0 - accessible from network"
                    ),
                    QuestionOption(
                        key="custom",
                        display="Custom host address",
                        help_text="Specify a custom IP address or hostname"
                    )
                ]
            ),
            
            # 10. Custom Server Host
            Question(
                id="custom_host",
                title="Enter custom host address:",
                description="Specify the IP address or hostname for the server to bind to.",
                question_type=QuestionType.TEXT,
                depends_on="server_accessibility", 
                depends_value="custom",
                default="127.0.0.1",
                validation={"pattern": r"^[\w\.\-]+$"}
            ),
            
            # 11. Server Port Configuration
            Question(
                id="server_port",
                title="What port should the server use?",
                description="Choose an available port number for the MCP server.",
                question_type=QuestionType.NUMERIC,
                depends_on="use_template",
                depends_value=False,
                default=8081,
                validation={"min": 1024, "max": 65535, "step": 1},
                impact_explanation="Make sure this port isn't used by other services"
            ),
            
            # 12. Server Title/Description
            Question(
                id="server_title",
                title="Enter a title for your memory server:",
                description="This helps identify the server in client configurations.",
                question_type=QuestionType.TEXT,
                depends_on="use_template",
                depends_value=False,
                default="Advanced Project Memory MCP Server"
            ),
            
            # 13. Domain Pattern Customization
            Question(
                id="customize_domains",
                title="Customize domain-specific keyword recognition?",
                description="Add keywords that are important in your specific work domain.",
                question_type=QuestionType.BOOLEAN,
                depends_on="use_template",
                depends_value=False,
                default=False,
                impact_explanation="Custom keywords help the system recognize domain-specific important content"
            ),
            
            # 14. Domain Categories
            Question(
                id="domain_categories",
                title="Which domain categories do you want to customize?",
                description="Select categories to add custom keywords for better content recognition.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                depends_on="customize_domains",
                depends_value=True,
                options=[
                    QuestionOption(
                        key="technology",
                        display="Technology & Development",
                        help_text="Programming languages, frameworks, tools, methodologies"
                    ),
                    QuestionOption(
                        key="business",
                        display="Business & Operations",
                        help_text="Business processes, metrics, customer terms, industry jargon"
                    ),
                    QuestionOption(
                        key="research",
                        display="Research & Analysis",
                        help_text="Research methods, statistical terms, academic concepts"
                    ),
                    QuestionOption(
                        key="creative",
                        display="Creative & Design",
                        help_text="Design principles, creative processes, artistic terms"
                    ),
                    QuestionOption(
                        key="custom",
                        display="Custom Categories",
                        help_text="Define your own categories and keywords"
                    )
                ]
            ),
            
            # 15. Technology Keywords (Dynamic question)
            Question(
                id="tech_keywords",
                title="Enter technology-related keywords (comma-separated):",
                description="Keywords that indicate important technical content in your domain.",
                question_type=QuestionType.TEXT,
                depends_on="domain_categories",
                depends_value="technology",
                impact_explanation="Examples: 'API', 'database', 'deployment', 'security', 'performance'"
            ),
            
            # 16. Business Keywords (Dynamic question)
            Question(
                id="business_keywords", 
                title="Enter business-related keywords (comma-separated):",
                description="Keywords that indicate important business content in your domain.",
                question_type=QuestionType.TEXT,
                depends_on="domain_categories",
                depends_value="business",
                impact_explanation="Examples: 'revenue', 'customer', 'strategy', 'growth', 'market'"
            ),
            
            # 17. Research Keywords (Dynamic question)
            Question(
                id="research_keywords",
                title="Enter research-related keywords (comma-separated):",
                description="Keywords that indicate important research content in your domain.",
                question_type=QuestionType.TEXT,
                depends_on="domain_categories", 
                depends_value="research",
                impact_explanation="Examples: 'hypothesis', 'analysis', 'data', 'methodology', 'findings'"
            ),
            
            # 18. Creative Keywords (Dynamic question)
            Question(
                id="creative_keywords",
                title="Enter creative-related keywords (comma-separated):",
                description="Keywords that indicate important creative content in your domain.",
                question_type=QuestionType.TEXT,
                depends_on="domain_categories",
                depends_value="creative", 
                impact_explanation="Examples: 'concept', 'design', 'inspiration', 'iteration', 'feedback'"
            ),
            
            # 19. Advanced Settings (Optional)
            Question(
                id="advanced_settings",
                title="Configure advanced settings?",
                description="Most users can skip this - defaults work well.",
                question_type=QuestionType.BOOLEAN,
                depends_on="use_template",
                depends_value=False,
                default=False,
                required=False
            ),
            
            # 8. Custom Importance Threshold (Advanced)
            Question(
                id="importance_threshold",
                title="Custom importance threshold for long-term memory?",
                description="Content with importance >= this value moves to long-term storage (0.1-1.0).",
                question_type=QuestionType.NUMERIC,
                default=0.7,
                depends_on="advanced_settings",
                depends_value=True,
                validation={"min": 0.1, "max": 1.0, "step": 0.1}
            ),
            
        ]
        
        return questions
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """Get a question by ID."""
        return self.question_map.get(question_id)
    
    def get_next_question(self, current_id: str, answers: Dict[str, Any]) -> Optional[Question]:
        """Get the next question based on current answers."""
        current_index = next(
            (i for i, q in enumerate(self.questions) if q.id == current_id), 
            -1
        )
        
        if current_index == -1 or current_index >= len(self.questions) - 1:
            return None
        
        # Find next applicable question
        for i in range(current_index + 1, len(self.questions)):
            question = self.questions[i]
            if self._should_ask_question(question, answers):
                return question
        
        return None
    
    def get_first_question(self) -> Question:
        """Get the first question in the flow."""
        return self.questions[0]
    
    def _should_ask_question(self, question: Question, answers: Dict[str, Any]) -> bool:
        """Check if a question should be asked based on dependencies."""
        if question.depends_on is None:
            return True
        
        dependency_answer = answers.get(question.depends_on)
        
        # Handle multiple choice dependencies (when depends_value is in a list)
        if isinstance(dependency_answer, list):
            return question.depends_value in dependency_answer
        
        return dependency_answer == question.depends_value
    
    def get_applicable_questions(self, answers: Dict[str, Any]) -> List[Question]:
        """Get all questions that should be asked given current answers."""
        applicable = []
        for question in self.questions:
            if self._should_ask_question(question, answers):
                applicable.append(question)
        return applicable
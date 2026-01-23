"""
Kafka Taint Tracker - Cross-Service Async Message Taint Analysis.

[20251220_FEATURE] v3.0.4 - Ninja Warrior Stage 3

This module tracks taint propagation across Kafka message boundaries:
- Detect tainted data sent to Kafka topics (data leak/exfiltration risk)
- Mark Kafka consumer handlers as taint sources
- Map topic-to-handler relationships within a codebase
- Bridge taint across async message boundaries

Kafka Security Concerns:
========================

1. DATA EXFILTRATION: Tainted user data sent to Kafka without sanitization
   - producer.send(topic, user_input)  # PII/secrets may leak to logs/analytics

2. INJECTION PROPAGATION: Tainted data consumed and used unsafely
   - msg = consumer.poll()  # Now tainted
   - db.execute(msg.value)  # SQL injection!

3. TOPIC POISONING: Attacker-controlled data in shared topics
   - Multiple services consume same topic
   - One compromised producer poisons all consumers

Supported Kafka Libraries:
- Python: kafka-python, confluent-kafka, aiokafka, faust
- Java: kafka-clients, spring-kafka
- JavaScript: kafkajs, node-rdkafka

Usage:
    tracker = KafkaTaintTracker()

    # Analyze a file for Kafka patterns
    result = tracker.analyze_file(source_code, "service.py")

    # Get all producers that send tainted data
    for producer in result.tainted_producers:
        print(f"RISK: {producer.topic} receives tainted data at line {producer.line}")

    # Get all consumer handlers (new taint sources)
    for consumer in result.consumer_handlers:
        print(f"SOURCE: {consumer.handler_name} consumes from {consumer.topic}")

    # Bridge taint across services
    bridge = tracker.create_taint_bridge(producer_result, consumer_result)
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


class KafkaLibrary(Enum):
    """Supported Kafka client libraries."""

    # Python
    KAFKA_PYTHON = "kafka-python"
    CONFLUENT_KAFKA = "confluent-kafka"
    AIOKAFKA = "aiokafka"
    FAUST = "faust"

    # Java
    KAFKA_CLIENTS = "kafka-clients"
    SPRING_KAFKA = "spring-kafka"

    # JavaScript
    KAFKAJS = "kafkajs"
    NODE_RDKAFKA = "node-rdkafka"

    UNKNOWN = "unknown"


class KafkaPatternType(Enum):
    """Types of Kafka patterns detected."""

    PRODUCER_SEND = auto()  # producer.send(topic, data)
    PRODUCER_PRODUCE = auto()  # producer.produce(topic, data)
    CONSUMER_POLL = auto()  # consumer.poll()
    CONSUMER_SUBSCRIBE = auto()  # consumer.subscribe([topics])
    CONSUMER_HANDLER = auto()  # @app.agent(topic) or @KafkaListener
    STREAM_PROCESSOR = auto()  # Kafka Streams / Faust agent
    ADMIN_OPERATION = auto()  # Topic creation, deletion


class KafkaRiskLevel(Enum):
    """Risk level for Kafka taint findings."""

    CRITICAL = "CRITICAL"  # Tainted data sent to Kafka, no sanitization
    HIGH = "HIGH"  # Tainted data with partial sanitization
    MEDIUM = "MEDIUM"  # Consumer handler without input validation
    LOW = "LOW"  # Informational (topic mapping)
    INFO = "INFO"  # No security concern


@dataclass
class KafkaProducer:
    """Represents a Kafka producer send operation."""

    topic: str
    topic_is_dynamic: bool = False  # Topic name from variable
    line: int = 0
    column: int = 0
    file_path: str = ""
    library: KafkaLibrary = KafkaLibrary.UNKNOWN
    data_variable: str | None = None  # Variable being sent
    is_tainted: bool = False
    taint_source: str | None = None  # Where taint originated
    key_variable: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    serializer: str | None = None  # json, avro, protobuf

    @property
    def risk_level(self) -> KafkaRiskLevel:
        """Determine risk level based on taint status."""
        if self.is_tainted and self.topic_is_dynamic:
            return KafkaRiskLevel.CRITICAL
        elif self.is_tainted:
            return KafkaRiskLevel.HIGH
        elif self.topic_is_dynamic:
            return KafkaRiskLevel.MEDIUM
        return KafkaRiskLevel.INFO


@dataclass
class KafkaConsumer:
    """Represents a Kafka consumer subscription/handler."""

    topics: list[str] = field(default_factory=list)
    handler_name: str | None = None  # Function/method name
    line: int = 0
    column: int = 0
    file_path: str = ""
    library: KafkaLibrary = KafkaLibrary.UNKNOWN
    pattern_type: KafkaPatternType = KafkaPatternType.CONSUMER_POLL
    group_id: str | None = None
    is_taint_source: bool = True  # All consumed data is potentially tainted
    deserializer: str | None = None  # json, avro, protobuf

    @property
    def taint_variables(self) -> list[str]:
        """Variables that should be marked as tainted from this consumer."""
        # Common patterns: msg, message, record, event, data
        return ["msg", "message", "record", "event", "data", "value", "payload"]


@dataclass
class KafkaTaintBridge:
    """
    Bridges taint from producer to consumer across async boundary.

    This is the key insight: when Service A sends tainted data to topic X,
    and Service B consumes from topic X, Service B's consumer should be
    marked as a taint source with the SAME taint origin.
    """

    topic: str
    producer: KafkaProducer
    consumers: list[KafkaConsumer] = field(default_factory=list)
    taint_propagates: bool = True
    original_taint_source: str | None = None

    @property
    def risk_summary(self) -> str:
        """Summarize the cross-service taint risk."""
        if not self.producer.is_tainted:
            return f"Topic '{self.topic}': No taint detected in producer"

        consumer_count = len(self.consumers)
        return (
            f"Topic '{self.topic}': TAINTED data from {self.producer.file_path}:{self.producer.line} "
            f"propagates to {consumer_count} consumer(s)"
        )


@dataclass
class KafkaTopicInfo:
    """Information about a Kafka topic's usage in the codebase."""

    name: str
    producers: list[KafkaProducer] = field(default_factory=list)
    consumers: list[KafkaConsumer] = field(default_factory=list)
    is_tainted: bool = False  # Any producer sends tainted data

    @property
    def producer_count(self) -> int:
        return len(self.producers)

    @property
    def consumer_count(self) -> int:
        return len(self.consumers)

    @property
    def has_multiple_producers(self) -> bool:
        """Multiple producers = harder to trace taint origin."""
        return len(self.producers) > 1


@dataclass
class KafkaAnalysisResult:
    """Result of analyzing a file/codebase for Kafka patterns."""

    file_path: str = ""
    producers: list[KafkaProducer] = field(default_factory=list)
    consumers: list[KafkaConsumer] = field(default_factory=list)
    topics: dict[str, KafkaTopicInfo] = field(default_factory=dict)
    detected_library: KafkaLibrary = KafkaLibrary.UNKNOWN
    errors: list[str] = field(default_factory=list)

    @property
    def tainted_producers(self) -> list[KafkaProducer]:
        """Get producers that send tainted data."""
        return [p for p in self.producers if p.is_tainted]

    @property
    def consumer_handlers(self) -> list[KafkaConsumer]:
        """Get consumer handlers (decorated functions)."""
        return [c for c in self.consumers if c.pattern_type == KafkaPatternType.CONSUMER_HANDLER]

    @property
    def has_taint_risks(self) -> bool:
        """Check if any taint risks were detected."""
        return len(self.tainted_producers) > 0

    @property
    def risk_count(self) -> dict[KafkaRiskLevel, int]:
        """Count findings by risk level."""
        counts: dict[KafkaRiskLevel, int] = {level: 0 for level in KafkaRiskLevel}
        for producer in self.producers:
            counts[producer.risk_level] += 1
        return counts

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Kafka Analysis: {self.file_path}",
            f"Library: {self.detected_library.value}",
            f"Producers: {len(self.producers)} ({len(self.tainted_producers)} tainted)",
            f"Consumers: {len(self.consumers)} ({len(self.consumer_handlers)} handlers)",
            f"Topics: {len(self.topics)}",
        ]

        if self.tainted_producers:
            lines.append("\n⚠️  TAINTED PRODUCERS:")
            for p in self.tainted_producers:
                lines.append(f"  - Line {p.line}: {p.topic} <- {p.data_variable} (from {p.taint_source})")

        if self.consumer_handlers:
            lines.append("\n🔍 CONSUMER HANDLERS (taint sources):")
            for c in self.consumer_handlers:
                topics_str = ", ".join(c.topics) if c.topics else "unknown"
                lines.append(f"  - {c.handler_name}: {topics_str}")

        return "\n".join(lines)


# =============================================================================
# Kafka Pattern Detection
# =============================================================================

# Python kafka-python patterns
KAFKA_PYTHON_PRODUCER_PATTERNS = [
    r'\.send\s*\(\s*["\']([^"\']+)["\']\s*,',  # producer.send("topic", data)
    r"\.send\s*\(\s*(\w+)\s*,",  # producer.send(topic_var, data)
]

KAFKA_PYTHON_CONSUMER_PATTERNS = [
    r"\.subscribe\s*\(\s*\[([^\]]+)\]",  # consumer.subscribe(["topic1", "topic2"])
    r"for\s+(\w+)\s+in\s+(\w+)",  # for msg in consumer:
    r"\.poll\s*\(",  # consumer.poll()
]

# Confluent Kafka patterns
CONFLUENT_PRODUCER_PATTERNS = [
    r'\.produce\s*\(\s*["\']([^"\']+)["\']\s*,',  # producer.produce("topic", data)
    r'\.produce\s*\(\s*topic\s*=\s*["\']([^"\']+)["\']',
]

CONFLUENT_CONSUMER_PATTERNS = [
    r"\.subscribe\s*\(\s*\[([^\]]+)\]",
    r"\.poll\s*\(",
]

# Faust patterns (Python streaming)
FAUST_PATTERNS = [
    r'@\w+\.agent\s*\(\s*["\']([^"\']+)["\']',  # @app.agent("topic")
    r'app\.topic\s*\(\s*["\']([^"\']+)["\']',  # app.topic("name")
]

# Java Spring Kafka patterns
SPRING_KAFKA_PATTERNS = [
    r'@KafkaListener\s*\(\s*topics\s*=\s*["\']([^"\']+)["\']',
    r"@KafkaListener\s*\(\s*topics\s*=\s*\{([^}]+)\}",
    r'kafkaTemplate\.send\s*\(\s*["\']([^"\']+)["\']',
    r"kafkaTemplate\.sendDefault\s*\(",
]

# JavaScript KafkaJS patterns
KAFKAJS_PATTERNS = [
    r'producer\.send\s*\(\s*\{\s*topic:\s*["\']([^"\']+)["\']',
    r'consumer\.subscribe\s*\(\s*\{\s*topic:\s*["\']([^"\']+)["\']',
    r"consumer\.run\s*\(\s*\{",
    r"\.eachMessage\s*\(",
]


class KafkaTaintTracker:
    """
    Tracks taint propagation through Kafka message boundaries.

    [20251220_FEATURE] v3.0.4 - Ninja Warrior Stage 3

    This tracker identifies:
    1. Producer sends where tainted data flows to Kafka
    2. Consumer handlers that introduce new taint sources
    3. Topic-to-handler mappings for cross-service analysis
    """

    def __init__(self, tainted_variables: set[str] | None = None):
        """
        Initialize the Kafka taint tracker.

        Args:
            tainted_variables: Set of variable names known to be tainted
        """
        self.tainted_variables = tainted_variables or set()
        self.topic_registry: dict[str, KafkaTopicInfo] = {}

        # Common taint sources (from request/input)
        self.default_taint_sources = {
            # Python Flask/Django
            "request.args",
            "request.form",
            "request.json",
            "request.data",
            "request.get_json",
            "request.values",
            "request.files",
            "request.GET",
            "request.POST",
            "request.body",
            # Python general
            "input",
            "sys.argv",
            "os.environ",
            # JavaScript Express
            "req.body",
            "req.query",
            "req.params",
            "req.headers",
            # Java Spring
            "@RequestBody",
            "@RequestParam",
            "@PathVariable",
        }

        # Variables commonly assigned from taint sources
        self.taint_propagation_vars = {
            "user_input",
            "data",
            "payload",
            "body",
            "params",
            "user_data",
            "request_data",
            "input_data",
            "form_data",
        }

    def analyze_file(
        self,
        source_code: str,
        file_path: str = "",
        language: str = "python",
    ) -> KafkaAnalysisResult:
        """
        Analyze source code for Kafka patterns and taint flow.

        Args:
            source_code: The source code to analyze
            file_path: Path to the file (for reporting)
            language: Programming language (python, java, javascript)

        Returns:
            KafkaAnalysisResult with detected patterns
        """
        result = KafkaAnalysisResult(file_path=file_path)

        # Detect library from imports
        result.detected_library = self._detect_library(source_code, language)

        # Find tainted variables in the code
        tainted_in_file = self._find_tainted_variables(source_code, language)
        self.tainted_variables.update(tainted_in_file)

        # Analyze based on language
        if language == "python":
            self._analyze_python(source_code, result)
        elif language == "java":
            self._analyze_java(source_code, result)
        elif language in ("javascript", "typescript"):
            self._analyze_javascript(source_code, result)
        else:
            result.errors.append(f"Unsupported language: {language}")

        # Build topic registry
        self._build_topic_registry(result)

        return result

    def _detect_library(self, source_code: str, language: str) -> KafkaLibrary:
        """Detect which Kafka library is being used."""
        if language == "python":
            if "confluent_kafka" in source_code:
                return KafkaLibrary.CONFLUENT_KAFKA
            elif "aiokafka" in source_code:
                return KafkaLibrary.AIOKAFKA
            elif "faust" in source_code:
                return KafkaLibrary.FAUST
            elif "kafka" in source_code.lower():
                return KafkaLibrary.KAFKA_PYTHON
        elif language == "java":
            if "spring" in source_code.lower() and "kafka" in source_code.lower():
                return KafkaLibrary.SPRING_KAFKA
            elif "kafka" in source_code.lower():
                return KafkaLibrary.KAFKA_CLIENTS
        elif language in ("javascript", "typescript"):
            if "kafkajs" in source_code.lower():
                return KafkaLibrary.KAFKAJS
            elif "rdkafka" in source_code.lower():
                return KafkaLibrary.NODE_RDKAFKA

        return KafkaLibrary.UNKNOWN

    def _find_tainted_variables(self, source_code: str, language: str) -> set[str]:
        """Find variables that are assigned from taint sources."""
        tainted = set()

        # Check for common taint source patterns
        for source in self.default_taint_sources:
            # Pattern: var = request.json
            pattern = rf"(\w+)\s*=\s*{re.escape(source)}"
            for match in re.finditer(pattern, source_code):
                tainted.add(match.group(1))

        # Check for common tainted variable names
        for var in self.taint_propagation_vars:
            if re.search(rf"\b{var}\b\s*=", source_code):
                tainted.add(var)

        return tainted

    def _analyze_python(self, source_code: str, result: KafkaAnalysisResult) -> None:
        """Analyze Python code for Kafka patterns."""
        lines = source_code.split("\n")

        # Parse AST for accurate analysis
        try:
            tree = ast.parse(source_code)
            self._analyze_python_ast(tree, result, lines)
        except SyntaxError as e:
            result.errors.append(f"Python syntax error: {e}")
            # Fall back to regex
            self._analyze_python_regex(source_code, result)

    def _outer_extract_string_value(self, node: ast.AST) -> str | None:
        """Wrapper for nested class to call outer extract_string_value."""
        return self._extract_string_value(node)

    def _outer_get_variable_name(self, node: ast.AST) -> str | None:
        """Wrapper for nested class to call outer get_variable_name."""
        return self._get_variable_name(node)

    def _analyze_python_ast(
        self,
        tree: ast.AST,
        result: KafkaAnalysisResult,
        lines: list[str],
    ) -> None:
        """Analyze Python AST for Kafka patterns."""

        # Reference to outer class for nested visitor
        outer_tracker = self

        class KafkaVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_function = None

            def _handle_function(self, node):
                """Handle both sync and async function definitions."""
                old_function = self.current_function
                self.current_function = node.name

                # Check for Faust @app.agent decorator
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr == "agent":
                                # Extract topic from decorator
                                if decorator.args:
                                    topic = outer_tracker._extract_string_value(decorator.args[0])
                                    if topic:
                                        consumer = KafkaConsumer(
                                            topics=[topic],
                                            handler_name=node.name,
                                            line=node.lineno,
                                            column=node.col_offset,
                                            file_path=result.file_path,
                                            library=KafkaLibrary.FAUST,
                                            pattern_type=KafkaPatternType.CONSUMER_HANDLER,
                                        )
                                        result.consumers.append(consumer)

                self.generic_visit(node)
                self.current_function = old_function

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._handle_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._handle_function(node)

            def visit_Call(self, node: ast.Call):
                # Check for producer.send() or producer.produce()
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr

                    if method_name == "send" and node.args:
                        # producer.send(topic, value)
                        topic = outer_tracker._extract_string_value(node.args[0])
                        topic_is_dynamic = topic is None
                        if topic is None:
                            topic = outer_tracker._get_variable_name(node.args[0]) or "dynamic"

                        data_var = None
                        is_tainted = False
                        taint_source = None

                        if len(node.args) > 1:
                            data_var = outer_tracker._get_variable_name(node.args[1])
                            if data_var and data_var in outer_tracker.tainted_variables:
                                is_tainted = True
                                taint_source = data_var

                        # Check keyword arguments
                        for kw in node.keywords:
                            if kw.arg == "value":
                                data_var = outer_tracker._get_variable_name(kw.value)
                                if data_var and data_var in outer_tracker.tainted_variables:
                                    is_tainted = True
                                    taint_source = data_var

                        producer = KafkaProducer(
                            topic=topic,
                            topic_is_dynamic=topic_is_dynamic,
                            line=node.lineno,
                            column=node.col_offset,
                            file_path=result.file_path,
                            library=result.detected_library,
                            data_variable=data_var,
                            is_tainted=is_tainted,
                            taint_source=taint_source,
                        )
                        result.producers.append(producer)

                    elif method_name == "produce" and node.args:
                        # confluent: producer.produce(topic, value)
                        topic = outer_tracker._extract_string_value(node.args[0])
                        topic_is_dynamic = topic is None
                        if topic is None:
                            topic = outer_tracker._get_variable_name(node.args[0]) or "dynamic"

                        data_var = None
                        is_tainted = False
                        taint_source = None

                        if len(node.args) > 1:
                            data_var = outer_tracker._get_variable_name(node.args[1])
                            if data_var and data_var in outer_tracker.tainted_variables:
                                is_tainted = True
                                taint_source = data_var

                        for kw in node.keywords:
                            if kw.arg == "value":
                                data_var = outer_tracker._get_variable_name(kw.value)
                                if data_var and data_var in outer_tracker.tainted_variables:
                                    is_tainted = True
                                    taint_source = data_var

                        producer = KafkaProducer(
                            topic=topic,
                            topic_is_dynamic=topic_is_dynamic,
                            line=node.lineno,
                            column=node.col_offset,
                            file_path=result.file_path,
                            library=KafkaLibrary.CONFLUENT_KAFKA,
                            data_variable=data_var,
                            is_tainted=is_tainted,
                            taint_source=taint_source,
                        )
                        result.producers.append(producer)

                    elif method_name == "subscribe":
                        # consumer.subscribe([topics])
                        if node.args and isinstance(node.args[0], ast.List):
                            topics = []
                            for elt in node.args[0].elts:
                                topic = outer_tracker._extract_string_value(elt)
                                if topic:
                                    topics.append(topic)

                            if topics:
                                consumer = KafkaConsumer(
                                    topics=topics,
                                    line=node.lineno,
                                    column=node.col_offset,
                                    file_path=result.file_path,
                                    library=result.detected_library,
                                    pattern_type=KafkaPatternType.CONSUMER_SUBSCRIBE,
                                )
                                result.consumers.append(consumer)

                    elif method_name == "poll":
                        # consumer.poll()
                        consumer = KafkaConsumer(
                            line=node.lineno,
                            column=node.col_offset,
                            file_path=result.file_path,
                            library=result.detected_library,
                            pattern_type=KafkaPatternType.CONSUMER_POLL,
                            handler_name=self.current_function,
                        )
                        result.consumers.append(consumer)

                # Check for KafkaConsumer() constructor call
                elif isinstance(node.func, ast.Name):
                    if node.func.id == "KafkaConsumer":
                        # KafkaConsumer('topic1', 'topic2', ...)
                        topics = []
                        for arg in node.args:
                            topic = outer_tracker._extract_string_value(arg)
                            if topic:
                                topics.append(topic)

                        if topics:
                            consumer = KafkaConsumer(
                                topics=topics,
                                line=node.lineno,
                                column=node.col_offset,
                                file_path=result.file_path,
                                library=result.detected_library,
                                pattern_type=KafkaPatternType.CONSUMER_SUBSCRIBE,
                            )
                            result.consumers.append(consumer)

                self.generic_visit(node)

        visitor = KafkaVisitor()
        visitor.visit(tree)

    def _extract_string_value(self, node: ast.AST) -> str | None:
        """Extract string value from AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return str(node.value) if isinstance(node.value, str) else None
        return None

    def _get_variable_name(self, node: ast.AST) -> str | None:
        """Get variable name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_variable_name(node.value)}.{node.attr}"
        return None

    def _analyze_python_regex(self, source_code: str, result: KafkaAnalysisResult) -> None:
        """Fallback regex-based analysis for Python."""
        lines = source_code.split("\n")

        for i, line in enumerate(lines, 1):
            # Check producer patterns
            for pattern in KAFKA_PYTHON_PRODUCER_PATTERNS + CONFLUENT_PRODUCER_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    topic = match.group(1)
                    topic_is_dynamic = not (topic.startswith('"') or topic.startswith("'"))

                    # Simple taint check - look for tainted vars in the line
                    is_tainted = any(var in line for var in self.tainted_variables)

                    producer = KafkaProducer(
                        topic=topic.strip("\"'"),
                        topic_is_dynamic=topic_is_dynamic,
                        line=i,
                        file_path=result.file_path,
                        library=result.detected_library,
                        is_tainted=is_tainted,
                    )
                    result.producers.append(producer)

            # Check consumer patterns
            for pattern in KAFKA_PYTHON_CONSUMER_PATTERNS + CONFLUENT_CONSUMER_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    consumer = KafkaConsumer(
                        line=i,
                        file_path=result.file_path,
                        library=result.detected_library,
                    )
                    result.consumers.append(consumer)

            # Check Faust patterns
            for pattern in FAUST_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    topic = match.group(1)
                    consumer = KafkaConsumer(
                        topics=[topic],
                        line=i,
                        file_path=result.file_path,
                        library=KafkaLibrary.FAUST,
                        pattern_type=KafkaPatternType.CONSUMER_HANDLER,
                    )
                    result.consumers.append(consumer)

    def _analyze_java(self, source_code: str, result: KafkaAnalysisResult) -> None:
        """Analyze Java code for Kafka patterns."""
        lines = source_code.split("\n")

        for i, line in enumerate(lines, 1):
            # Spring @KafkaListener
            for pattern in SPRING_KAFKA_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    topics_str = match.group(1)
                    # Parse topics - may be single or multiple
                    topics = [t.strip().strip("\"'") for t in topics_str.split(",")]

                    # Find the method name on the next non-empty line
                    handler_name = None
                    for j in range(i, min(i + 5, len(lines))):
                        method_match = re.search(
                            r"(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(",
                            lines[j],
                        )
                        if method_match:
                            handler_name = method_match.group(1)
                            break

                    if "send" in pattern.lower():
                        # KafkaTemplate.send
                        is_tainted = any(var in line for var in self.tainted_variables)
                        producer = KafkaProducer(
                            topic=topics[0] if topics else "unknown",
                            line=i,
                            file_path=result.file_path,
                            library=KafkaLibrary.SPRING_KAFKA,
                            is_tainted=is_tainted,
                        )
                        result.producers.append(producer)
                    else:
                        # @KafkaListener
                        consumer = KafkaConsumer(
                            topics=topics,
                            handler_name=handler_name,
                            line=i,
                            file_path=result.file_path,
                            library=KafkaLibrary.SPRING_KAFKA,
                            pattern_type=KafkaPatternType.CONSUMER_HANDLER,
                        )
                        result.consumers.append(consumer)

    def _analyze_javascript(self, source_code: str, result: KafkaAnalysisResult) -> None:
        """Analyze JavaScript/TypeScript code for Kafka patterns."""
        lines = source_code.split("\n")

        # First, do multiline pattern matching on full source
        # KafkaJS producer.send with object argument
        send_pattern = re.compile(
            r'producer\.send\s*\(\s*\{\s*topic:\s*["\']([^"\']+)["\']',
            re.MULTILINE | re.DOTALL,
        )
        for match in send_pattern.finditer(source_code):
            topic = match.group(1)
            # Find line number
            line_num = source_code[: match.start()].count("\n") + 1
            is_tainted = any(var in source_code[match.start() : match.start() + 200] for var in self.tainted_variables)

            producer = KafkaProducer(
                topic=topic,
                line=line_num,
                file_path=result.file_path,
                library=KafkaLibrary.KAFKAJS,
                is_tainted=is_tainted,
            )
            result.producers.append(producer)

        # Line-by-line analysis for other patterns
        for i, line in enumerate(lines, 1):
            # Skip if already found producer on this line
            if any(p.line == i for p in result.producers):
                continue

            for pattern in KAFKAJS_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    if "subscribe" in pattern:
                        topic = match.group(1) if match.groups() else "unknown"
                        consumer = KafkaConsumer(
                            topics=[topic],
                            line=i,
                            file_path=result.file_path,
                            library=KafkaLibrary.KAFKAJS,
                            pattern_type=KafkaPatternType.CONSUMER_SUBSCRIBE,
                        )
                        result.consumers.append(consumer)
                    elif "eachMessage" in pattern or "run" in pattern:
                        consumer = KafkaConsumer(
                            line=i,
                            file_path=result.file_path,
                            library=KafkaLibrary.KAFKAJS,
                            pattern_type=KafkaPatternType.CONSUMER_HANDLER,
                        )
                        result.consumers.append(consumer)

    def _build_topic_registry(self, result: KafkaAnalysisResult) -> None:
        """Build topic registry from analysis results."""
        for producer in result.producers:
            if producer.topic not in result.topics:
                result.topics[producer.topic] = KafkaTopicInfo(name=producer.topic)
            result.topics[producer.topic].producers.append(producer)
            if producer.is_tainted:
                result.topics[producer.topic].is_tainted = True

        for consumer in result.consumers:
            for topic in consumer.topics:
                if topic not in result.topics:
                    result.topics[topic] = KafkaTopicInfo(name=topic)
                result.topics[topic].consumers.append(consumer)

    def create_taint_bridge(
        self,
        producer_result: KafkaAnalysisResult,
        consumer_result: KafkaAnalysisResult,
    ) -> list[KafkaTaintBridge]:
        """
        Create taint bridges between producer and consumer results.

        This connects taint across async message boundaries:
        - If producer sends tainted data to topic X
        - And consumer reads from topic X
        - Then consumer's data should be marked as tainted

        Args:
            producer_result: Analysis result with producers
            consumer_result: Analysis result with consumers

        Returns:
            List of taint bridges
        """
        bridges = []

        for producer in producer_result.producers:
            if not producer.is_tainted:
                continue

            # Find consumers of this topic
            matching_consumers = [c for c in consumer_result.consumers if producer.topic in c.topics]

            if matching_consumers:
                bridge = KafkaTaintBridge(
                    topic=producer.topic,
                    producer=producer,
                    consumers=matching_consumers,
                    taint_propagates=True,
                    original_taint_source=producer.taint_source,
                )
                bridges.append(bridge)

        return bridges

    def mark_consumer_as_taint_source(
        self,
        consumer: KafkaConsumer,
        original_taint: str | None = None,
    ) -> dict[str, str]:
        """
        Generate taint source mappings for a consumer handler.

        Returns dict mapping variable names to taint origins.

        Args:
            consumer: The consumer to mark
            original_taint: Where the taint originally came from

        Returns:
            Dict mapping variable names to taint descriptions
        """
        taint_origin = original_taint or f"kafka:{','.join(consumer.topics)}"

        return {var: f"KAFKA_CONSUMER({taint_origin})" for var in consumer.taint_variables}

    def get_security_findings(
        self,
        result: KafkaAnalysisResult,
    ) -> list[dict[str, Any]]:
        """
        Generate security findings from analysis result.

        Returns findings in a format compatible with Code Scalpel's
        security reporting infrastructure.
        """
        findings = []

        for producer in result.tainted_producers:
            findings.append(
                {
                    "type": "KAFKA_TAINTED_PRODUCER",
                    "severity": producer.risk_level.value,
                    "cwe": "CWE-200",  # Exposure of Sensitive Information
                    "message": f"Tainted data sent to Kafka topic '{producer.topic}'",
                    "file": producer.file_path,
                    "line": producer.line,
                    "column": producer.column,
                    "taint_source": producer.taint_source,
                    "data_variable": producer.data_variable,
                    "topic": producer.topic,
                    "recommendation": (
                        "Validate and sanitize data before sending to Kafka. "
                        "Consider: 1) Schema validation, 2) PII scrubbing, "
                        "3) Encryption for sensitive data."
                    ),
                }
            )

        # Mark consumer handlers as taint sources (informational)
        for consumer in result.consumer_handlers:
            findings.append(
                {
                    "type": "KAFKA_CONSUMER_TAINT_SOURCE",
                    "severity": "INFO",
                    "cwe": "CWE-20",  # Improper Input Validation
                    "message": f"Consumer handler '{consumer.handler_name}' receives external data",
                    "file": consumer.file_path,
                    "line": consumer.line,
                    "topics": consumer.topics,
                    "recommendation": (
                        "Treat consumed messages as untrusted input. "
                        "Validate message schema and sanitize before use in "
                        "SQL queries, file operations, or command execution."
                    ),
                }
            )

        return findings


# =============================================================================
# Convenience Functions
# =============================================================================


def analyze_kafka_file(
    file_path: str,
    tainted_variables: set[str] | None = None,
) -> KafkaAnalysisResult:
    """
    Analyze a file for Kafka taint patterns.

    Args:
        file_path: Path to the file to analyze
        tainted_variables: Known tainted variables

    Returns:
        KafkaAnalysisResult with findings
    """
    path = Path(file_path)

    if not path.exists():
        result = KafkaAnalysisResult(file_path=file_path)
        result.errors.append(f"File not found: {file_path}")
        return result

    # Determine language from extension
    ext = path.suffix.lower()
    language_map = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
    }
    language = language_map.get(ext, "python")

    source_code = path.read_text(encoding="utf-8")

    tracker = KafkaTaintTracker(tainted_variables)
    return tracker.analyze_file(source_code, file_path, language)


def analyze_kafka_codebase(
    directory: str,
    tainted_variables: set[str] | None = None,
    extensions: list[str] | None = None,
) -> list[KafkaAnalysisResult]:
    """
    Analyze an entire codebase for Kafka taint patterns.

    Args:
        directory: Root directory to scan
        tainted_variables: Known tainted variables
        extensions: File extensions to scan (default: .py, .java, .js, .ts)

    Returns:
        List of KafkaAnalysisResult for each file with Kafka patterns
    """
    if extensions is None:
        extensions = [".py", ".java", ".js", ".ts", ".jsx", ".tsx"]

    results = []
    root = Path(directory)

    tracker = KafkaTaintTracker(tainted_variables)

    for ext in extensions:
        for file_path in root.rglob(f"*{ext}"):
            # Skip common non-source directories
            if any(part in file_path.parts for part in ["node_modules", ".venv", "venv", "__pycache__", ".git"]):
                continue

            try:
                source_code = file_path.read_text(encoding="utf-8")

                # Quick check - does it mention Kafka?
                if "kafka" not in source_code.lower():
                    continue

                language = "python" if ext == ".py" else "java" if ext == ".java" else "javascript"
                result = tracker.analyze_file(source_code, str(file_path), language)

                # Only include files with Kafka patterns
                if result.producers or result.consumers:
                    results.append(result)

            except Exception as e:
                result = KafkaAnalysisResult(file_path=str(file_path))
                result.errors.append(str(e))
                results.append(result)

    return results


def get_kafka_taint_bridges(
    results: list[KafkaAnalysisResult],
) -> list[KafkaTaintBridge]:
    """
    Find all taint bridges across multiple analysis results.

    This is the key function for cross-service taint tracking:
    connects tainted producers in one service to consumers in another.

    Args:
        results: List of analysis results from different files/services

    Returns:
        List of taint bridges
    """
    all_producers = []
    all_consumers = []

    for result in results:
        all_producers.extend(result.producers)
        all_consumers.extend(result.consumers)

    bridges = []

    for producer in all_producers:
        if not producer.is_tainted:
            continue

        matching_consumers = [
            c for c in all_consumers if producer.topic in c.topics and c.file_path != producer.file_path
        ]

        if matching_consumers:
            bridge = KafkaTaintBridge(
                topic=producer.topic,
                producer=producer,
                consumers=matching_consumers,
                taint_propagates=True,
                original_taint_source=producer.taint_source,
            )
            bridges.append(bridge)

    return bridges


# [20251225_FEATURE] Export public API for type checkers
__all__ = [
    "KafkaTaintTracker",
    "KafkaProducer",
    "KafkaConsumer",
    "KafkaTaintBridge",
    "KafkaTopicInfo",
    "KafkaAnalysisResult",
    "KafkaLibrary",
    "KafkaPatternType",
    "KafkaRiskLevel",
    "analyze_kafka_file",
    "analyze_kafka_codebase",
    "get_kafka_taint_bridges",
]

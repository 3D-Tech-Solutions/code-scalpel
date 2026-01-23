"""
Tests for Kafka Taint Tracker.

[20251220_FEATURE] v3.0.4 - Ninja Warrior Stage 3

Tests cover:
- Producer detection (kafka-python, confluent, Spring, KafkaJS)
- Consumer detection (poll, subscribe, handlers)
- Taint tracking through Kafka boundaries
- Topic registry building
- Cross-service taint bridging
"""

import pytest

from code_scalpel.integrations.protocol_analyzers.kafka.taint_tracker import (
    KafkaAnalysisResult,
    KafkaConsumer,
    KafkaLibrary,
    KafkaPatternType,
    KafkaProducer,
    KafkaRiskLevel,
    KafkaTaintTracker,
    KafkaTopicInfo,
    analyze_kafka_file,
    get_kafka_taint_bridges,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def tracker():
    """Create a KafkaTaintTracker instance."""
    return KafkaTaintTracker()


@pytest.fixture
def tracker_with_tainted():
    """Create tracker with known tainted variables."""
    return KafkaTaintTracker(tainted_variables={"user_input", "payload", "data"})


@pytest.fixture
def python_producer_code():
    """Python code with Kafka producer."""
    return """
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers='localhost:9092')

def send_user_data(user_input):
    # This sends tainted data!
    producer.send("user-events", value=user_input)
    producer.send("analytics", value={"action": "click"})
"""


@pytest.fixture
def python_consumer_code():
    """Python code with Kafka consumer."""
    return """
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers='localhost:9092',
    group_id='my-group'
)

consumer.subscribe(['user-events', 'notifications'])

for msg in consumer:
    process_message(msg.value)
"""


@pytest.fixture
def faust_agent_code():
    """Faust streaming agent code."""
    return """
import faust

app = faust.App('myapp', broker='kafka://localhost:9092')

@app.agent("user-events")
async def process_users(stream):
    async for event in stream:
        yield process(event)

@app.agent("orders")
async def process_orders(stream):
    async for order in stream:
        save_order(order)
"""


@pytest.fixture
def spring_kafka_code():
    """Java Spring Kafka code."""
    return """
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;

@Service
public class UserEventService {

    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    @KafkaListener(topics = "user-events")
    public void handleUserEvent(String message) {
        processEvent(message);
    }

    @KafkaListener(topics = {"orders", "payments"})
    public void handleOrders(String message) {
        processOrder(message);
    }

    public void sendEvent(String data) {
        kafkaTemplate.send("user-events", data);
    }
}
"""


@pytest.fixture
def kafkajs_code():
    """JavaScript KafkaJS code."""
    return """
const { Kafka } = require('kafkajs');

const kafka = new Kafka({ brokers: ['localhost:9092'] });
const producer = kafka.producer();
const consumer = kafka.consumer({ groupId: 'test-group' });

async function sendMessage(payload) {
    await producer.send({
        topic: 'user-events',
        messages: [{ value: JSON.stringify(payload) }]
    });
}

await consumer.subscribe({ topic: 'user-events', fromBeginning: true });

await consumer.run({
    eachMessage: async ({ topic, partition, message }) => {
        console.log(message.value.toString());
    }
});
"""


# =============================================================================
# Test Python Producer Detection
# =============================================================================


class TestPythonProducerDetection:
    """Test detection of Python Kafka producers."""

    def test_detect_kafka_python_send(self, tracker):
        """Test detection of producer.send() calls."""
        code = """
producer.send("my-topic", value=data)
producer.send("other-topic", key=key, value=message)
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert len(result.producers) == 2
        assert result.producers[0].topic == "my-topic"
        assert result.producers[1].topic == "other-topic"

    def test_detect_tainted_producer(self, tracker_with_tainted):
        """Test detection of tainted data in producer."""
        code = """
user_input = request.json
producer.send("events", value=user_input)
"""
        result = tracker_with_tainted.analyze_file(code, "test.py", "python")

        assert len(result.producers) == 1
        assert result.producers[0].is_tainted
        assert result.producers[0].taint_source == "user_input"

    def test_detect_confluent_produce(self, tracker):
        """Test detection of confluent producer.produce() calls."""
        code = """
from confluent_kafka import Producer
producer = Producer({'bootstrap.servers': 'localhost:9092'})
producer.produce("my-topic", value=data)
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert result.detected_library == KafkaLibrary.CONFLUENT_KAFKA
        assert len(result.producers) == 1
        assert result.producers[0].topic == "my-topic"

    def test_dynamic_topic_detection(self, tracker):
        """Test detection of dynamic topic names."""
        code = """
topic = get_topic_for_event(event_type)
producer.send(topic, value=data)
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert len(result.producers) == 1
        assert result.producers[0].topic_is_dynamic

    def test_producer_risk_levels(self, tracker_with_tainted):
        """Test risk level assignment for producers."""
        code = """
# Critical: tainted data + dynamic topic
producer.send(dynamic_topic, value=user_input)
# High: tainted data, static topic
producer.send("events", value=payload)
# Medium: dynamic topic only
producer.send(topic_var, value=safe_data)
# Info: static topic, safe data
producer.send("logs", value={"level": "info"})
"""
        result = tracker_with_tainted.analyze_file(code, "test.py", "python")

        # Verify we detect producers with different risk levels
        assert len(result.producers) >= 2
        tainted = [p for p in result.producers if p.is_tainted]
        assert len(tainted) >= 1


# =============================================================================
# Test Python Consumer Detection
# =============================================================================


class TestPythonConsumerDetection:
    """Test detection of Python Kafka consumers."""

    def test_detect_subscribe(self, tracker):
        """Test detection of consumer.subscribe() calls."""
        code = """
consumer.subscribe(['topic1', 'topic2'])
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert len(result.consumers) == 1
        assert "topic1" in result.consumers[0].topics
        assert "topic2" in result.consumers[0].topics

    def test_detect_poll(self, tracker):
        """Test detection of consumer.poll() calls."""
        code = """
def process_messages():
    msg = consumer.poll(timeout=1.0)
    if msg:
        handle(msg)
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert any(c.pattern_type == KafkaPatternType.CONSUMER_POLL for c in result.consumers)

    def test_consumer_is_taint_source(self, tracker):
        """Test that consumers are marked as taint sources."""
        code = """
consumer.subscribe(['events'])
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert len(result.consumers) == 1
        assert result.consumers[0].is_taint_source


# =============================================================================
# Test Faust Agent Detection
# =============================================================================


class TestFaustAgentDetection:
    """Test detection of Faust streaming agents."""

    def test_detect_faust_agent(self, tracker, faust_agent_code):
        """Test detection of @app.agent decorators."""
        result = tracker.analyze_file(faust_agent_code, "app.py", "python")

        assert result.detected_library == KafkaLibrary.FAUST
        handlers = [c for c in result.consumers if c.pattern_type == KafkaPatternType.CONSUMER_HANDLER]
        assert len(handlers) == 2

    def test_faust_handler_topics(self, tracker, faust_agent_code):
        """Test topic extraction from Faust agents."""
        result = tracker.analyze_file(faust_agent_code, "app.py", "python")

        handlers = result.consumer_handlers
        topics = [t for h in handlers for t in h.topics]
        assert "user-events" in topics
        assert "orders" in topics

    def test_faust_handler_names(self, tracker, faust_agent_code):
        """Test handler name extraction."""
        result = tracker.analyze_file(faust_agent_code, "app.py", "python")

        handler_names = [h.handler_name for h in result.consumer_handlers]
        assert "process_users" in handler_names
        assert "process_orders" in handler_names


# =============================================================================
# Test Java/Spring Kafka Detection
# =============================================================================


class TestSpringKafkaDetection:
    """Test detection of Spring Kafka patterns."""

    def test_detect_kafka_listener(self, tracker, spring_kafka_code):
        """Test detection of @KafkaListener annotations."""
        result = tracker.analyze_file(spring_kafka_code, "Service.java", "java")

        assert result.detected_library == KafkaLibrary.SPRING_KAFKA
        handlers = result.consumer_handlers
        assert len(handlers) >= 2

    def test_detect_kafka_listener_topics(self, tracker, spring_kafka_code):
        """Test topic extraction from @KafkaListener."""
        result = tracker.analyze_file(spring_kafka_code, "Service.java", "java")

        all_topics = []
        for handler in result.consumer_handlers:
            all_topics.extend(handler.topics)

        assert "user-events" in all_topics

    def test_detect_kafka_template_send(self, tracker, spring_kafka_code):
        """Test detection of kafkaTemplate.send()."""
        result = tracker.analyze_file(spring_kafka_code, "Service.java", "java")

        assert len(result.producers) >= 1
        assert any(p.topic == "user-events" for p in result.producers)


# =============================================================================
# Test JavaScript/KafkaJS Detection
# =============================================================================


class TestKafkaJSDetection:
    """Test detection of KafkaJS patterns."""

    def test_detect_kafkajs_producer(self, tracker, kafkajs_code):
        """Test detection of KafkaJS producer.send()."""
        result = tracker.analyze_file(kafkajs_code, "service.js", "javascript")

        assert result.detected_library == KafkaLibrary.KAFKAJS
        assert len(result.producers) >= 1
        assert result.producers[0].topic == "user-events"

    def test_detect_kafkajs_consumer(self, tracker, kafkajs_code):
        """Test detection of KafkaJS consumer patterns."""
        result = tracker.analyze_file(kafkajs_code, "service.js", "javascript")

        assert len(result.consumers) >= 1

    def test_detect_each_message_handler(self, tracker, kafkajs_code):
        """Test detection of eachMessage handler."""
        result = tracker.analyze_file(kafkajs_code, "service.js", "javascript")

        handlers = [c for c in result.consumers if c.pattern_type == KafkaPatternType.CONSUMER_HANDLER]
        assert len(handlers) >= 1


# =============================================================================
# Test Topic Registry
# =============================================================================


class TestTopicRegistry:
    """Test topic registry building."""

    def test_build_topic_registry(self, tracker):
        """Test building topic registry from analysis."""
        code = """
producer.send("events", value=data)
producer.send("events", value=other_data)
consumer.subscribe(['events', 'logs'])
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert "events" in result.topics
        assert result.topics["events"].producer_count == 2
        assert result.topics["events"].consumer_count == 1

    def test_topic_taint_status(self, tracker_with_tainted):
        """Test topic taint status tracking."""
        code = """
producer.send("tainted-topic", value=user_input)
producer.send("clean-topic", value=safe_data)
"""
        result = tracker_with_tainted.analyze_file(code, "test.py", "python")

        assert result.topics["tainted-topic"].is_tainted
        assert not result.topics.get("clean-topic", KafkaTopicInfo("")).is_tainted

    def test_multiple_producers_detection(self, tracker):
        """Test detection of multiple producers for same topic."""
        code = """
producer1.send("shared-topic", value=data1)
producer2.send("shared-topic", value=data2)
producer3.send("shared-topic", value=data3)
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert "shared-topic" in result.topics
        assert result.topics["shared-topic"].has_multiple_producers


# =============================================================================
# Test Taint Bridge
# =============================================================================


class TestTaintBridge:
    """Test cross-service taint bridging."""

    def test_create_taint_bridge(self, tracker_with_tainted):
        """Test creating taint bridge between producer and consumer."""
        producer_code = """
user_input = request.json
producer.send("events", value=user_input)
"""
        consumer_code = """
consumer.subscribe(['events'])
msg = consumer.poll()
"""
        producer_result = tracker_with_tainted.analyze_file(producer_code, "producer.py", "python")
        consumer_result = tracker_with_tainted.analyze_file(consumer_code, "consumer.py", "python")

        bridges = tracker_with_tainted.create_taint_bridge(producer_result, consumer_result)

        assert len(bridges) == 1
        assert bridges[0].topic == "events"
        assert bridges[0].taint_propagates

    def test_bridge_tracks_original_taint(self, tracker_with_tainted):
        """Test that bridge tracks original taint source."""
        producer_code = """
payload = request.json
producer.send("events", value=payload)
"""
        consumer_code = """
consumer.subscribe(['events'])
"""
        producer_result = tracker_with_tainted.analyze_file(producer_code, "producer.py", "python")
        consumer_result = tracker_with_tainted.analyze_file(consumer_code, "consumer.py", "python")

        bridges = tracker_with_tainted.create_taint_bridge(producer_result, consumer_result)

        assert len(bridges) == 1
        assert bridges[0].original_taint_source == "payload"

    def test_no_bridge_for_clean_data(self, tracker):
        """Test no bridge created for non-tainted data."""
        producer_code = """
producer.send("events", value={"type": "heartbeat"})
"""
        consumer_code = """
consumer.subscribe(['events'])
"""
        producer_result = tracker.analyze_file(producer_code, "producer.py", "python")
        consumer_result = tracker.analyze_file(consumer_code, "consumer.py", "python")

        bridges = tracker.create_taint_bridge(producer_result, consumer_result)

        assert len(bridges) == 0


# =============================================================================
# Test Consumer as Taint Source
# =============================================================================


class TestConsumerAsTaintSource:
    """Test marking consumers as taint sources."""

    def test_consumer_taint_variables(self, tracker):
        """Test consumer provides list of taint variables."""
        consumer = KafkaConsumer(topics=["events"])

        assert "msg" in consumer.taint_variables
        assert "message" in consumer.taint_variables
        assert "payload" in consumer.taint_variables

    def test_mark_consumer_as_source(self, tracker):
        """Test marking consumer handler as taint source."""
        consumer = KafkaConsumer(
            topics=["events", "orders"],
            handler_name="process_event",
        )

        taint_map = tracker.mark_consumer_as_taint_source(consumer)

        assert "msg" in taint_map
        assert "kafka:events,orders" in taint_map["msg"]

    def test_mark_with_original_taint(self, tracker):
        """Test marking with original taint information."""
        consumer = KafkaConsumer(topics=["events"])

        taint_map = tracker.mark_consumer_as_taint_source(consumer, original_taint="request.json from producer.py:15")

        assert "request.json" in taint_map["msg"]


# =============================================================================
# Test Security Findings Generation
# =============================================================================


class TestSecurityFindings:
    """Test security finding generation."""

    def test_generate_tainted_producer_finding(self, tracker_with_tainted):
        """Test generating finding for tainted producer."""
        code = """
user_input = request.json
producer.send("events", value=user_input)
"""
        result = tracker_with_tainted.analyze_file(code, "test.py", "python")
        findings = tracker_with_tainted.get_security_findings(result)

        tainted_findings = [f for f in findings if f["type"] == "KAFKA_TAINTED_PRODUCER"]
        assert len(tainted_findings) == 1
        assert tainted_findings[0]["cwe"] == "CWE-200"

    def test_generate_consumer_handler_finding(self, tracker, faust_agent_code):
        """Test generating informational finding for consumer handler."""
        result = tracker.analyze_file(faust_agent_code, "app.py", "python")
        findings = tracker.get_security_findings(result)

        handler_findings = [f for f in findings if f["type"] == "KAFKA_CONSUMER_TAINT_SOURCE"]
        assert len(handler_findings) >= 1
        assert handler_findings[0]["severity"] == "INFO"

    def test_finding_has_recommendation(self, tracker_with_tainted):
        """Test that findings include recommendations."""
        code = """
data = request.json
producer.send("events", value=data)
"""
        result = tracker_with_tainted.analyze_file(code, "test.py", "python")
        findings = tracker_with_tainted.get_security_findings(result)

        for finding in findings:
            assert "recommendation" in finding
            assert len(finding["recommendation"]) > 0


# =============================================================================
# Test Analysis Result Properties
# =============================================================================


class TestAnalysisResultProperties:
    """Test KafkaAnalysisResult properties."""

    def test_tainted_producers_property(self, tracker_with_tainted):
        """Test tainted_producers property."""
        code = """
user_input = request.json
producer.send("events", value=user_input)
producer.send("logs", value={"type": "info"})
"""
        result = tracker_with_tainted.analyze_file(code, "test.py", "python")

        assert len(result.tainted_producers) == 1
        assert result.tainted_producers[0].topic == "events"

    def test_consumer_handlers_property(self, tracker, faust_agent_code):
        """Test consumer_handlers property."""
        result = tracker.analyze_file(faust_agent_code, "app.py", "python")

        assert len(result.consumer_handlers) == 2

    def test_has_taint_risks_property(self, tracker_with_tainted):
        """Test has_taint_risks property."""
        tainted_code = """
user_input = request.json
producer.send("events", value=user_input)
"""
        clean_code = """
producer.send("events", value={"type": "info"})
"""

        tainted_result = tracker_with_tainted.analyze_file(tainted_code, "test.py", "python")
        clean_result = tracker_with_tainted.analyze_file(clean_code, "test.py", "python")

        assert tainted_result.has_taint_risks
        assert not clean_result.has_taint_risks

    def test_risk_count_property(self, tracker_with_tainted):
        """Test risk_count property."""
        code = """
user_input = request.json
producer.send("events", value=user_input)
producer.send("logs", value={"type": "info"})
"""
        result = tracker_with_tainted.analyze_file(code, "test.py", "python")

        risk_counts = result.risk_count
        assert KafkaRiskLevel.HIGH in risk_counts or KafkaRiskLevel.CRITICAL in risk_counts

    def test_summary_generation(self, tracker_with_tainted, python_producer_code):
        """Test summary generation."""
        result = tracker_with_tainted.analyze_file(python_producer_code, "test.py", "python")
        summary = result.summary()

        assert "Kafka Analysis" in summary
        assert "Producers:" in summary


# =============================================================================
# Test Library Detection
# =============================================================================


class TestLibraryDetection:
    """Test Kafka library detection."""

    def test_detect_kafka_python(self, tracker):
        """Test detecting kafka-python library."""
        code = "from kafka import KafkaProducer"
        result = tracker.analyze_file(code, "test.py", "python")

        assert result.detected_library == KafkaLibrary.KAFKA_PYTHON

    def test_detect_confluent_kafka(self, tracker):
        """Test detecting confluent-kafka library."""
        code = "from confluent_kafka import Producer"
        result = tracker.analyze_file(code, "test.py", "python")

        assert result.detected_library == KafkaLibrary.CONFLUENT_KAFKA

    def test_detect_aiokafka(self, tracker):
        """Test detecting aiokafka library."""
        code = "from aiokafka import AIOKafkaProducer"
        result = tracker.analyze_file(code, "test.py", "python")

        assert result.detected_library == KafkaLibrary.AIOKAFKA

    def test_detect_faust(self, tracker):
        """Test detecting faust library."""
        code = "import faust"
        result = tracker.analyze_file(code, "test.py", "python")

        assert result.detected_library == KafkaLibrary.FAUST

    def test_detect_spring_kafka(self, tracker):
        """Test detecting Spring Kafka."""
        code = "import org.springframework.kafka.annotation.KafkaListener;"
        result = tracker.analyze_file(code, "Service.java", "java")

        assert result.detected_library == KafkaLibrary.SPRING_KAFKA

    def test_detect_kafkajs(self, tracker):
        """Test detecting KafkaJS."""
        code = "const { Kafka } = require('kafkajs');"
        result = tracker.analyze_file(code, "service.js", "javascript")

        assert result.detected_library == KafkaLibrary.KAFKAJS


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_code(self, tracker):
        """Test handling empty code."""
        result = tracker.analyze_file("", "test.py", "python")

        assert len(result.producers) == 0
        assert len(result.consumers) == 0
        assert len(result.errors) == 0

    def test_code_without_kafka(self, tracker):
        """Test code without Kafka patterns."""
        code = """
def hello():
    print("Hello, World!")
"""
        result = tracker.analyze_file(code, "test.py", "python")

        assert len(result.producers) == 0
        assert len(result.consumers) == 0

    def test_syntax_error_fallback(self, tracker):
        """Test fallback to regex on syntax error."""
        code = """
producer.send("events", value=data
# Missing closing paren - syntax error
"""
        result = tracker.analyze_file(code, "test.py", "python")

        # Should still detect via regex fallback
        assert len(result.errors) >= 1 or len(result.producers) >= 1

    def test_unsupported_language(self, tracker):
        """Test unsupported language handling."""
        result = tracker.analyze_file("some code", "test.rb", "ruby")

        assert "Unsupported language" in result.errors[0]


# =============================================================================
# Test Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_analyze_kafka_file_not_found(self):
        """Test handling of non-existent file."""
        result = analyze_kafka_file("/nonexistent/path.py")

        assert "not found" in result.errors[0].lower()

    def test_get_kafka_taint_bridges_multiple_files(self):
        """Test getting taint bridges from multiple results."""
        # Create mock results
        result1 = KafkaAnalysisResult(file_path="producer.py")
        result1.producers.append(
            KafkaProducer(
                topic="events",
                is_tainted=True,
                taint_source="request.json",
                file_path="producer.py",  # Must set file_path on producer
            )
        )

        result2 = KafkaAnalysisResult(file_path="consumer.py")
        result2.consumers.append(
            KafkaConsumer(
                topics=["events"],
                handler_name="handle_event",
                file_path="consumer.py",  # Must set file_path on consumer (different from producer)
            )
        )

        bridges = get_kafka_taint_bridges([result1, result2])

        assert len(bridges) == 1
        assert bridges[0].topic == "events"


# =============================================================================
# Test Integration
# =============================================================================


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, tracker_with_tainted):
        """Test complete analysis workflow."""
        # Producer service
        producer_code = """
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode()
)

def handle_request():
    user_input = request.get_json()  # TAINT SOURCE

    # Process and send to Kafka - TAINTED!
    producer.send("user-events", value=user_input)

    # This is safe
    producer.send("metrics", value={"count": 1})
"""

        # Consumer service
        consumer_code = """
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode())
)

def process_messages():
    for msg in consumer:
        # msg.value is now TAINTED from producer
        db.execute(f"INSERT INTO events VALUES ({msg.value})")  # SQLi!
"""

        # Analyze both services
        producer_result = tracker_with_tainted.analyze_file(producer_code, "producer_service.py", "python")
        consumer_result = tracker_with_tainted.analyze_file(consumer_code, "consumer_service.py", "python")

        # Verify producer analysis
        assert producer_result.detected_library == KafkaLibrary.KAFKA_PYTHON
        assert len(producer_result.producers) == 2
        assert len(producer_result.tainted_producers) == 1
        assert producer_result.tainted_producers[0].topic == "user-events"

        # Verify consumer analysis
        assert len(consumer_result.consumers) >= 1

        # Create taint bridge
        bridges = tracker_with_tainted.create_taint_bridge(producer_result, consumer_result)

        # Verify bridge
        assert len(bridges) == 1
        assert bridges[0].topic == "user-events"
        assert bridges[0].taint_propagates

        # Generate security findings
        findings = tracker_with_tainted.get_security_findings(producer_result)
        assert any(f["type"] == "KAFKA_TAINTED_PRODUCER" for f in findings)

    def test_multi_language_analysis(self, tracker_with_tainted):
        """Test analyzing code in multiple languages."""
        python_code = """
from kafka import KafkaProducer
user_input = request.json
producer.send("events", value=user_input)
"""
        java_code = """
import org.springframework.kafka.annotation.KafkaListener;

@KafkaListener(topics = "events")
public void handleEvent(String message) {
    processEvent(message);
}
"""
        js_code = """
const { Kafka } = require('kafkajs');
await producer.send({
    topic: 'events',
    messages: [{ value: JSON.stringify(payload) }]
});
"""

        py_result = tracker_with_tainted.analyze_file(python_code, "producer.py", "python")
        java_result = tracker_with_tainted.analyze_file(java_code, "Consumer.java", "java")
        js_result = tracker_with_tainted.analyze_file(js_code, "producer.js", "javascript")

        assert py_result.detected_library == KafkaLibrary.KAFKA_PYTHON
        assert java_result.detected_library == KafkaLibrary.SPRING_KAFKA
        assert js_result.detected_library == KafkaLibrary.KAFKAJS

        # Get cross-service bridges
        bridges = get_kafka_taint_bridges([py_result, java_result, js_result])

        # Python tainted producer -> Java consumer
        assert any(b.topic == "events" for b in bridges)

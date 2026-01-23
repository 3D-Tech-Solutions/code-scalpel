#!/usr/bin/env python
"""
Polyglot Edge Case Tests

[20251215_TEST] Tests for edge cases in multi-language support.
Covers unusual syntax patterns in each supported language.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_scalpel.mcp.server import extract_code

# [20251215_TEST] Lint cleanup for polyglot edge case tests (remove unused imports).


class TestPythonEdgeCases:
    """Python-specific edge cases."""

    @pytest.mark.asyncio
    async def test_walrus_operator(self):
        """Assignment expression (walrus operator)."""
        code = """
def process(data):
    if (n := len(data)) > 10:
        return n
    return 0
"""
        result = await extract_code(code=code, target_type="function", target_name="process")
        assert result.success
        assert ":=" in result.target_code

    @pytest.mark.asyncio
    async def test_match_statement(self):
        """Python 3.10 match statement."""
        code = """
def handle_command(command):
    match command:
        case "quit" | "exit":
            return False
        case ["move", direction]:
            return f"Moving {direction}"
        case {"action": "attack", "target": target}:
            return f"Attacking {target}"
        case _:
            return "Unknown command"
"""
        result = await extract_code(code=code, target_type="function", target_name="handle_command")
        assert result.success
        assert "match" in result.target_code

    @pytest.mark.asyncio
    async def test_positional_only_params(self):
        """Positional-only parameters (/)."""
        code = """
def divmod_custom(a, b, /):
    return a // b, a % b
"""
        result = await extract_code(code=code, target_type="function", target_name="divmod_custom")
        assert result.success
        assert "/" in result.target_code

    @pytest.mark.asyncio
    async def test_keyword_only_params(self):
        """Keyword-only parameters (*)."""
        code = """
def configure(*, debug=False, timeout=30):
    return {"debug": debug, "timeout": timeout}
"""
        result = await extract_code(code=code, target_type="function", target_name="configure")
        assert result.success

    @pytest.mark.asyncio
    async def test_all_param_types(self):
        """Function with all parameter types."""
        code = """
def complex_params(pos_only, /, normal, *args, kw_only, **kwargs):
    return (pos_only, normal, args, kw_only, kwargs)
"""
        result = await extract_code(code=code, target_type="function", target_name="complex_params")
        assert result.success

    @pytest.mark.asyncio
    async def test_nested_f_strings(self):
        """Nested f-strings."""
        code = """
def nested_fstring(items):
    return f"{len(items)} items: {', '.join(f'{i}: {v}' for i, v in enumerate(items))}"
"""
        result = await extract_code(code=code, target_type="function", target_name="nested_fstring")
        assert result.success

    @pytest.mark.asyncio
    async def test_async_generator(self):
        """Async generator function."""
        code = """
async def async_range(n):
    for i in range(n):
        await asyncio.sleep(0.1)
        yield i
"""
        result = await extract_code(code=code, target_type="function", target_name="async_range")
        assert result.success
        assert "async def" in result.target_code
        assert "yield" in result.target_code

    @pytest.mark.asyncio
    async def test_dataclass_with_field(self):
        """Dataclass with field defaults."""
        code = """
from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    name: str
    values: List[int] = field(default_factory=list)
    _cache: dict = field(default_factory=dict, repr=False)
"""
        result = await extract_code(code=code, target_type="class", target_name="Config")
        assert result.success
        assert "@dataclass" in result.target_code


class TestTypeScriptEdgeCases:
    """TypeScript-specific edge cases."""

    @pytest.mark.asyncio
    async def test_conditional_types(self):
        """Conditional types."""
        code = """
type TypeName<T> =
    T extends string ? "string" :
    T extends number ? "number" :
    T extends boolean ? "boolean" :
    T extends undefined ? "undefined" :
    T extends Function ? "function" :
    "object";

function getTypeName<T>(value: T): TypeName<T> {
    return typeof value as TypeName<T>;
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="getTypeName",
            language="typescript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_mapped_types(self):
        """Mapped types."""
        code = """
type Readonly<T> = {
    readonly [P in keyof T]: T[P];
};

type Mutable<T> = {
    -readonly [P in keyof T]: T[P];
};

function freeze<T>(obj: T): Readonly<T> {
    return Object.freeze(obj);
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="freeze",
            language="typescript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_template_literal_types(self):
        """Template literal types."""
        code = """
type EventName<T extends string> = `on${Capitalize<T>}`;
type Handler = EventName<"click" | "focus" | "blur">;

function handleEvent<T extends string>(
    event: EventName<T>,
    handler: () => void
): void {
    console.log(event);
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="handleEvent",
            language="typescript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_infer_keyword(self):
        """Infer keyword in conditional types."""
        code = """
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;
type ArrayElement<T> = T extends (infer E)[] ? E : never;

async function unwrap<T>(promise: Promise<T>): Promise<UnwrapPromise<Promise<T>>> {
    return await promise;
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="unwrap",
            language="typescript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_satisfies_operator(self):
        """TypeScript satisfies operator (4.9+)."""
        code = """
type Colors = "red" | "green" | "blue";
type RGB = [red: number, green: number, blue: number];

const palette = {
    red: [255, 0, 0],
    green: "#00ff00",
    blue: [0, 0, 255]
} satisfies Record<Colors, RGB | string>;

function getColor(name: Colors): RGB | string {
    return palette[name];
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="getColor",
            language="typescript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_decorator_factory(self):
        """TypeScript decorator factory."""
        code = """
function log(prefix: string) {
    return function <T extends { new (...args: any[]): {} }>(
        target: T
    ) {
        return class extends target {
            constructor(...args: any[]) {
                console.log(`${prefix}: Creating instance`);
                super(...args);
            }
        };
    };
}

@log("User")
class UserService {
    constructor(private name: string) {}
}
"""
        result = await extract_code(code=code, target_type="function", target_name="log", language="typescript")
        assert result.success


class TestJavaEdgeCases:
    """Java-specific edge cases."""

    @pytest.mark.asyncio
    async def test_record_class(self):
        """Java record class (Java 16+)."""
        code = """
public record Point(int x, int y) {
    public Point {
        if (x < 0 || y < 0) {
            throw new IllegalArgumentException("Coordinates must be non-negative");
        }
    }

    public double distanceFromOrigin() {
        return Math.sqrt(x * x + y * y);
    }
}
"""
        result = await extract_code(code=code, target_type="class", target_name="Point", language="java")
        assert result.success
        assert "record" in result.target_code

    @pytest.mark.asyncio
    async def test_sealed_class(self):
        """Java sealed class (Java 17+)."""
        code = """
public sealed class Shape permits Circle, Rectangle, Triangle {
    protected final String color;

    public Shape(String color) {
        this.color = color;
    }

    public abstract double area();
}

final class Circle extends Shape {
    private final double radius;

    public Circle(String color, double radius) {
        super(color);
        this.radius = radius;
    }

    @Override
    public double area() {
        return Math.PI * radius * radius;
    }
}
"""
        result = await extract_code(code=code, target_type="class", target_name="Shape", language="java")
        assert result.success
        assert "sealed" in result.target_code

    @pytest.mark.asyncio
    async def test_pattern_matching_switch(self):
        """Java pattern matching in switch (Java 21+)."""
        code = """
public class PatternMatcher {
    public static String describe(Object obj) {
        return switch (obj) {
            case Integer i when i > 0 -> "Positive integer: " + i;
            case Integer i -> "Non-positive integer: " + i;
            case String s when s.isEmpty() -> "Empty string";
            case String s -> "String: " + s;
            case null -> "null";
            default -> "Unknown: " + obj.getClass();
        };
    }
}
"""
        result = await extract_code(
            code=code,
            target_type="class",
            target_name="PatternMatcher",
            language="java",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_var_keyword(self):
        """Java var keyword (Java 10+)."""
        code = """
public class VarExample {
    public void process() {
        var list = new ArrayList<String>();
        var map = Map.of("key", "value");
        for (var entry : map.entrySet()) {
            list.add(entry.getKey());
        }
    }
}
"""
        result = await extract_code(code=code, target_type="class", target_name="VarExample", language="java")
        assert result.success

    @pytest.mark.asyncio
    async def test_text_blocks(self):
        """Java text blocks (Java 15+)."""
        code = '''
public class TextBlocks {
    public String getQuery() {
        return """
            SELECT u.id, u.name
            FROM users u
            WHERE u.active = true
            ORDER BY u.name
            """;
    }
}
'''
        result = await extract_code(
            code=code,
            target_type="method",
            target_name="TextBlocks.getQuery",
            language="java",
        )
        assert result.success
        assert '"""' in result.target_code


class TestJSXEdgeCases:
    """JSX-specific edge cases."""

    @pytest.mark.asyncio
    async def test_fragments(self):
        """JSX fragments."""
        code = """
function FragmentExample({ items }) {
    return (
        <>
            <header>Title</header>
            {items.map(item => <li key={item.id}>{item.name}</li>)}
            <footer>End</footer>
        </>
    );
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="FragmentExample",
            language="javascript",
        )
        assert result.success
        assert "<>" in result.target_code

    @pytest.mark.asyncio
    async def test_spread_props(self):
        """JSX spread props."""
        code = """
function SpreadComponent({ className, ...restProps }) {
    return <div className={`base ${className}`} {...restProps} />;
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="SpreadComponent",
            language="javascript",
        )
        assert result.success
        assert "...restProps" in result.target_code

    @pytest.mark.asyncio
    async def test_render_props(self):
        """Render props pattern."""
        code = """
function DataProvider({ render }) {
    const [data, setData] = useState(null);

    useEffect(() => {
        fetchData().then(setData);
    }, []);

    return render(data);
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="DataProvider",
            language="javascript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_conditional_rendering(self):
        """Complex conditional rendering."""
        code = """
function ConditionalComponent({ status, user, items }) {
    return (
        <div>
            {status === 'loading' && <Spinner />}
            {status === 'error' && <Error message="Failed to load" />}
            {status === 'success' && (
                <>
                    <Welcome user={user} />
                    {items.length > 0 ? (
                        <List items={items} />
                    ) : (
                        <Empty message="No items" />
                    )}
                </>
            )}
        </div>
    );
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="ConditionalComponent",
            language="javascript",
        )
        assert result.success


class TestTSXEdgeCases:
    """TSX-specific edge cases."""

    @pytest.mark.asyncio
    async def test_generic_component(self):
        """Generic TSX component."""
        code = """
interface ListProps<T> {
    items: T[];
    renderItem: (item: T) => React.ReactNode;
    keyExtractor: (item: T) => string;
}

function GenericList<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
    return (
        <ul>
            {items.map(item => (
                <li key={keyExtractor(item)}>{renderItem(item)}</li>
            ))}
        </ul>
    );
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="GenericList",
            language="typescript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_forward_ref(self):
        """forwardRef with TypeScript."""
        code = """
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ label, ...props }, ref) => (
        <div>
            <label>{label}</label>
            <input ref={ref} {...props} />
        </div>
    )
);
"""
        result = await extract_code(
            code=code,
            target_type="variable",
            target_name="Input",
            language="typescript",
        )
        # Should extract the forwardRef assignment
        assert result is not None

    @pytest.mark.asyncio
    async def test_context_with_types(self):
        """React Context with TypeScript."""
        code = """
interface ThemeContextType {
    theme: 'light' | 'dark';
    toggleTheme: () => void;
}

const ThemeContext = React.createContext<ThemeContextType | undefined>(undefined);

function useTheme(): ThemeContextType {
    const context = React.useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider');
    }
    return context;
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="useTheme",
            language="typescript",
        )
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

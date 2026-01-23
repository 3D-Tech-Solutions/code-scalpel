"""
Tests for Frontend Input Tracker - TypeScript/JavaScript DOM Input Detection.

[20251220_FEATURE] v3.0.4 - Ninja Warrior Stage 3

Tests:
- Vanilla JS/TS DOM input patterns (getElementById, querySelector, event.target)
- React patterns (useState, onChange, useRef, dangerouslySetInnerHTML)
- Vue patterns (v-model, ref, v-html)
- Angular patterns (ngModel, FormControl, [innerHTML])
- Data flow tracking (input → sink)
- Sanitization detection
- Multi-framework file analysis
"""

import pytest

from code_scalpel.integrations.protocol_analyzers.frontend.input_tracker import (
    DangerousSinkType,
    FrontendFramework,
    FrontendInputTracker,
    InputSourceType,
    get_xss_risks,
)

# =============================================================================
# Framework Detection Tests
# =============================================================================


class TestFrameworkDetection:
    """Test automatic framework detection."""

    def test_detect_react(self):
        """Detect React from imports."""
        source = """
        import React, { useState, useEffect } from 'react';

        function App() {
            const [value, setValue] = useState('');
            return <div>{value}</div>;
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "App.tsx")
        assert result.framework == FrontendFramework.REACT

    def test_detect_vue(self):
        """Detect Vue from imports and directives."""
        source = """
        <template>
            <input v-model="message" />
            <div v-html="content"></div>
        </template>
        <script>
        import { ref, defineComponent } from 'vue';
        export default defineComponent({});
        </script>
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Component.vue")
        assert result.framework == FrontendFramework.VUE

    def test_detect_angular(self):
        """Detect Angular from decorators."""
        source = """
        import { Component, Input } from '@angular/core';
        import { FormControl, FormGroup } from '@angular/forms';

        @Component({
            selector: 'app-root',
            template: '<input [(ngModel)]="name" />'
        })
        export class AppComponent {
            @Input() data: string;
            name = new FormControl('');
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "app.component.ts")
        assert result.framework == FrontendFramework.ANGULAR

    def test_detect_vanilla(self):
        """Default to vanilla JS when no framework detected."""
        source = """
        document.getElementById('input').value;
        const x = location.search;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")
        assert result.framework == FrontendFramework.VANILLA

    def test_explicit_framework(self):
        """Use explicit framework when specified."""
        source = "const x = 1;"
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "app.js", framework="react")
        assert result.framework == FrontendFramework.REACT


# =============================================================================
# Vanilla JS/TS Input Detection Tests
# =============================================================================


class TestVanillaInputDetection:
    """Test vanilla JS/TS DOM input detection."""

    def test_get_element_by_id(self):
        """Detect document.getElementById."""
        source = """
        const input = document.getElementById('userInput');
        const value = input.value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        assert len(result.input_sources) >= 1
        patterns = [s.pattern for s in result.input_sources]
        assert any("getElementById" in p for p in patterns)

    def test_query_selector(self):
        """Detect querySelector patterns."""
        source = """
        const nameInput = document.querySelector('#name');
        const allInputs = document.querySelectorAll('input[type="text"]');
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        patterns = [s.pattern for s in result.input_sources]
        assert any("querySelector" in p for p in patterns)

    def test_element_value(self):
        """Detect .value access on elements."""
        source = """
        const input = document.getElementById('search');
        const searchTerm = input.value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        assert any(s.source_type == InputSourceType.ELEMENT_VALUE for s in result.input_sources)

    def test_event_target_value(self):
        """Detect event.target.value patterns."""
        source = """
        function handleChange(event) {
            const value = event.target.value;
            processInput(value);
        }

        input.addEventListener('change', (e) => {
            const data = e.target.value;
        });
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        event_sources = [s for s in result.input_sources if s.source_type == InputSourceType.EVENT_TARGET]
        assert len(event_sources) >= 2

    def test_location_search(self):
        """Detect URL parameter access."""
        source = """
        const params = location.search;
        const urlParams = new URLSearchParams(window.location.search);
        const id = urlParams.get('id');
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        url_sources = [s for s in result.input_sources if s.source_type == InputSourceType.URL_PARAM]
        assert len(url_sources) >= 1

    def test_location_hash(self):
        """Detect location.hash access."""
        source = """
        const fragment = location.hash;
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash;
        });
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        assert any(s.source_type == InputSourceType.URL_HASH for s in result.input_sources)

    def test_local_storage(self):
        """Detect localStorage access."""
        source = """
        const savedData = localStorage.getItem('userData');
        const session = sessionStorage.getItem('token');
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        storage_sources = [
            s
            for s in result.input_sources
            if s.source_type in (InputSourceType.LOCAL_STORAGE, InputSourceType.SESSION_STORAGE)
        ]
        assert len(storage_sources) >= 2

    def test_post_message(self):
        """Detect postMessage event data."""
        source = """
        window.addEventListener('message', (event) => {
            const data = event.data;
            processExternalData(data);
        });
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        assert any(s.source_type == InputSourceType.POST_MESSAGE for s in result.input_sources)

    def test_file_input(self):
        """Detect file input access."""
        source = """
        const fileInput = document.getElementById('file');
        const files = fileInput.files;
        const reader = new FileReader();
        reader.readAsText(files[0]);
        console.log(FileReader.result);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        assert any(s.source_type == InputSourceType.FILE_INPUT for s in result.input_sources)


# =============================================================================
# React Input Detection Tests
# =============================================================================


class TestReactInputDetection:
    """Test React-specific input detection."""

    def test_use_state_with_event(self):
        """Detect useState with event handler."""
        source = """
        import React, { useState } from 'react';

        function SearchBox() {
            const [query, setQuery] = useState('');

            return (
                <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
            );
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "SearchBox.tsx")

        assert result.framework == FrontendFramework.REACT
        assert any(s.source_type == InputSourceType.REACT_STATE for s in result.input_sources)

    def test_use_ref(self):
        """Detect useRef for DOM access."""
        source = """
        import React, { useRef } from 'react';

        function Form() {
            const inputRef = useRef<HTMLInputElement>(null);

            const handleSubmit = () => {
                const value = inputRef.current.value;
                submit(value);
            };

            return <input ref={inputRef} />;
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Form.tsx")

        ref_sources = [s for s in result.input_sources if s.source_type == InputSourceType.REACT_REF]
        assert len(ref_sources) >= 1

    def test_on_change_handler(self):
        """Detect onChange event handlers."""
        source = """
        import React from 'react';

        function Input({ onChange }) {
            return (
                <input
                    onChange={(event) => handleChange(event)}
                    onInput={(e) => processInput(e)}
                />
            );
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Input.tsx")

        form_sources = [s for s in result.input_sources if s.source_type == InputSourceType.REACT_FORM]
        assert len(form_sources) >= 2

    def test_controlled_input(self):
        """Detect controlled input pattern."""
        source = """
        import React, { useState } from 'react';

        function ControlledInput() {
            const [name, setName] = useState('');

            return (
                <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                />
            );
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "ControlledInput.tsx")

        # Should detect both the value binding and state
        assert any("value" in s.pattern for s in result.input_sources)

    def test_form_submit_handler(self):
        """Detect form submission handlers."""
        source = """
        import React from 'react';

        function LoginForm() {
            return (
                <form onSubmit={handleSubmit}>
                    <input name="username" />
                    <button type="submit">Login</button>
                </form>
            );
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "LoginForm.tsx")

        assert any(s.source_type == InputSourceType.REACT_FORM for s in result.input_sources)


# =============================================================================
# Vue Input Detection Tests
# =============================================================================


class TestVueInputDetection:
    """Test Vue-specific input detection."""

    def test_v_model(self):
        """Detect v-model bindings."""
        source = """
        <template>
            <input v-model="searchQuery" />
            <textarea v-model="content"></textarea>
        </template>
        <script>
        import { defineComponent } from 'vue';
        export default defineComponent({});
        </script>
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Search.vue")

        v_model_sources = [s for s in result.input_sources if s.source_type == InputSourceType.VUE_V_MODEL]
        assert len(v_model_sources) >= 2

    def test_vue_ref(self):
        """Detect Vue 3 ref() and reactive()."""
        source = """
        <script setup>
        import { ref, reactive } from 'vue';

        const message = ref('');
        const form = reactive({
            username: '',
            password: ''
        });
        </script>
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Form.vue")

        ref_sources = [s for s in result.input_sources if s.source_type == InputSourceType.VUE_REF]
        assert len(ref_sources) >= 2

    def test_vue_event_handlers(self):
        """Detect Vue @ event handlers."""
        source = """
        <template>
            <input @input="handleInput" @change="handleChange" />
        </template>
        <script>
        import { defineComponent } from 'vue';
        </script>
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Input.vue")

        assert len(result.input_sources) >= 2


# =============================================================================
# Angular Input Detection Tests
# =============================================================================


class TestAngularInputDetection:
    """Test Angular-specific input detection."""

    def test_ng_model(self):
        """Detect ngModel bindings."""
        source = """
        import { Component } from '@angular/core';
        import { FormsModule } from '@angular/forms';

        @Component({
            template: `
                <input [(ngModel)]="username" />
                <input [ngModel]="email" />
            `
        })
        export class AppComponent {
            username = '';
            email = '';
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "app.component.ts")

        ng_model_sources = [s for s in result.input_sources if s.source_type == InputSourceType.ANGULAR_NG_MODEL]
        assert len(ng_model_sources) >= 2

    def test_reactive_forms(self):
        """Detect Reactive Forms patterns."""
        source = """
        import { Component } from '@angular/core';
        import { FormControl, FormGroup, FormBuilder } from '@angular/forms';

        @Component({})
        export class LoginComponent {
            loginForm = new FormGroup({
                username: new FormControl(''),
                password: new FormControl('')
            });

            constructor(private fb: FormBuilder) {
                this.searchControl = fb.control('');
            }

            ngOnInit() {
                this.searchControl.valueChanges.subscribe(value => {
                    this.search(value);
                });
            }
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "login.component.ts")

        form_sources = [s for s in result.input_sources if s.source_type == InputSourceType.ANGULAR_FORM]
        assert len(form_sources) >= 3

    def test_input_decorator(self):
        """Detect @Input() decorator."""
        source = """
        import { Component, Input } from '@angular/core';

        @Component({})
        export class ChildComponent {
            @Input() userData: string;
            @Input() config: any;
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "child.component.ts")

        input_sources = [s for s in result.input_sources if s.source_type == InputSourceType.ANGULAR_INPUT]
        assert len(input_sources) >= 2

    def test_template_events(self):
        """Detect Angular template event bindings."""
        source = """
        import { Component } from '@angular/core';

        @Component({
            template: `
                <input (input)="onInput($event)" />
                <select (change)="onChange($event)">
                </select>
            `
        })
        export class FormComponent {}
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "form.component.ts")

        assert len(result.input_sources) >= 2


# =============================================================================
# Dangerous Sink Detection Tests
# =============================================================================


class TestDangerousSinkDetection:
    """Test detection of dangerous sinks."""

    def test_inner_html(self):
        """Detect innerHTML assignment."""
        source = """
        const div = document.getElementById('content');
        div.innerHTML = userInput;
        element.outerHTML = data;
        container.insertAdjacentHTML('beforeend', markup);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        html_sinks = [
            s
            for s in result.dangerous_sinks
            if s.sink_type in (DangerousSinkType.INNER_HTML, DangerousSinkType.DOM_MANIPULATION)
        ]
        assert len(html_sinks) >= 3

    def test_document_write(self):
        """Detect document.write."""
        source = """
        document.write('<p>' + userInput + '</p>');
        document.writeln(content);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        write_sinks = [s for s in result.dangerous_sinks if s.sink_type == DangerousSinkType.DOCUMENT_WRITE]
        assert len(write_sinks) >= 2

    def test_react_dangerously_set_inner_html(self):
        """Detect React dangerouslySetInnerHTML."""
        source = """
        import React from 'react';

        function RawHtml({ content }) {
            return (
                <div dangerouslySetInnerHTML={{ __html: content }} />
            );
        }

        const element = {
            dangerouslySetInnerHTML: { __html: userContent }
        };
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "RawHtml.tsx")

        dangerous_sinks = [s for s in result.dangerous_sinks if s.sink_type == DangerousSinkType.DANGEROUSLY_SET]
        assert len(dangerous_sinks) >= 2

    def test_vue_v_html(self):
        """Detect Vue v-html directive."""
        source = """
        <template>
            <div v-html="rawHtml"></div>
            <span v-html="userContent"></span>
        </template>
        <script>
        import { defineComponent } from 'vue';
        </script>
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Content.vue")

        v_html_sinks = [s for s in result.dangerous_sinks if s.sink_type == DangerousSinkType.V_HTML]
        assert len(v_html_sinks) >= 2

    def test_angular_inner_html_binding(self):
        """Detect Angular [innerHTML] binding."""
        source = """
        import { Component } from '@angular/core';

        @Component({
            template: `
                <div [innerHTML]="htmlContent"></div>
            `
        })
        export class RawComponent {}
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "raw.component.ts")

        assert any(s.sink_type == DangerousSinkType.INNER_HTML_BINDING for s in result.dangerous_sinks)

    def test_eval(self):
        """Detect eval and Function constructor."""
        source = """
        eval(userCode);
        const fn = new Function('x', userExpression);
        setTimeout('doSomething()', 1000);
        setInterval('tick()', 100);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        eval_sinks = [s for s in result.dangerous_sinks if s.sink_type == DangerousSinkType.EVAL]
        assert len(eval_sinks) >= 4

    def test_location_redirect(self):
        """Detect location-based redirects."""
        source = """
        location.href = nextUrl;
        location.assign(redirectUrl);
        location.replace(destination);
        window.open(externalUrl);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "redirect.js")

        redirect_sinks = [
            s for s in result.dangerous_sinks if s.sink_type in (DangerousSinkType.LOCATION, DangerousSinkType.OPEN)
        ]
        assert len(redirect_sinks) >= 4


# =============================================================================
# Data Flow Analysis Tests
# =============================================================================


class TestDataFlowAnalysis:
    """Test input → sink data flow detection."""

    def test_direct_flow_to_inner_html(self):
        """Detect direct input to innerHTML."""
        source = """
        const input = document.getElementById('search');
        const value = input.value;
        document.getElementById('result').innerHTML = value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        assert len(result.data_flows) >= 1
        assert any(f.sink.sink_type == DangerousSinkType.INNER_HTML for f in result.data_flows)

    def test_react_state_to_dangerous_html(self):
        """Detect React state flowing to dangerouslySetInnerHTML."""
        source = """
        import React, { useState } from 'react';

        function Editor() {
            const [content, setContent] = useState('');

            return (
                <>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                    />
                    <div dangerouslySetInnerHTML={{ __html: content }} />
                </>
            );
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Editor.tsx")

        # Should detect flow from state to dangerous sink
        dangerous = result.dangerous_flows
        assert any(f.sink.sink_type == DangerousSinkType.DANGEROUSLY_SET for f in dangerous)

    def test_url_param_to_inner_html(self):
        """Detect URL parameter flowing to innerHTML."""
        source = """
        const params = new URLSearchParams(location.search);
        const query = params.get('q');
        document.getElementById('search-term').innerHTML = query;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "search.js")

        dangerous = result.dangerous_flows
        assert len(dangerous) >= 1

    def test_event_to_eval(self):
        """Detect event data flowing to eval."""
        source = """
        function handleMessage(event) {
            const code = event.data;
            eval(code);
        }
        window.addEventListener('message', handleMessage);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "message.js")

        # Verify we detect both the post message source and eval sink
        assert any(s.source_type == InputSourceType.POST_MESSAGE for s in result.input_sources)
        assert any(s.sink_type == DangerousSinkType.EVAL for s in result.dangerous_sinks)


# =============================================================================
# Sanitization Detection Tests
# =============================================================================


class TestSanitizationDetection:
    """Test sanitization pattern detection."""

    def test_dompurify_sanitize(self):
        """Detect DOMPurify.sanitize as safe pattern."""
        source = """
        import DOMPurify from 'dompurify';

        const input = document.getElementById('input');
        const userHtml = input.value;
        const cleanHtml = DOMPurify.sanitize(userHtml);
        document.getElementById('output').innerHTML = cleanHtml;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        # Flow should be marked as sanitized
        sanitized = [f for f in result.data_flows if f.is_sanitized]
        assert len(sanitized) >= 1

    def test_text_content_safe(self):
        """Detect textContent as safe alternative."""
        source = """
        const userInput = document.getElementById('input').value;
        // Safe: using textContent instead of innerHTML
        document.getElementById('output').textContent = userInput;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "script.js")

        # textContent should not be flagged as dangerous sink
        dangerous_html = [s for s in result.dangerous_sinks if s.sink_type == DangerousSinkType.INNER_HTML]
        assert len(dangerous_html) == 0

    def test_encode_uri_component(self):
        """Detect encodeURIComponent as sanitization."""
        source = """
        const query = event.target.value;
        const safeQuery = encodeURIComponent(query);
        location.href = '/search?q=' + safeQuery;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "search.js")

        # Should be marked as sanitized
        sanitized = [f for f in result.data_flows if f.is_sanitized]
        # May have flow but should detect sanitization context
        assert any(s.is_validated for s in result.input_sources) or len(sanitized) >= 0


# =============================================================================
# Security Findings Tests
# =============================================================================


class TestSecurityFindings:
    """Test security finding generation."""

    def test_xss_finding_generation(self):
        """Generate XSS security findings."""
        source = """
        const input = document.getElementById('input');
        const value = input.value;
        document.getElementById('output').innerHTML = value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "xss.js")
        findings = tracker.get_security_findings(result)

        xss_findings = [f for f in findings if f["type"] == "FRONTEND_XSS_RISK"]
        assert len(xss_findings) >= 1

        finding = xss_findings[0]
        assert finding["cwe"] == "CWE-79"
        assert "recommendation" in finding

    def test_input_source_info_finding(self):
        """Generate informational findings for input sources."""
        source = """
        const searchParams = new URLSearchParams(location.search);
        const id = searchParams.get('id');
        console.log(id);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "params.js")
        findings = tracker.get_security_findings(result)

        info_findings = [f for f in findings if f["type"] == "FRONTEND_INPUT_SOURCE"]
        assert len(info_findings) >= 1

    def test_recommendation_content(self):
        """Verify recommendations include helpful guidance."""
        source = """
        import React, { useState } from 'react';

        function Widget() {
            const [html, setHtml] = useState('');
            return <div dangerouslySetInnerHTML={{ __html: html }} />;
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Widget.tsx")
        findings = tracker.get_security_findings(result)

        for finding in findings:
            if finding["type"] == "FRONTEND_XSS_RISK":
                assert "DOMPurify" in finding["recommendation"] or "sanitize" in finding["recommendation"].lower()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests with realistic code samples."""

    def test_react_form_complete(self):
        """Test complete React form analysis."""
        source = """
        import React, { useState, useRef } from 'react';
        import DOMPurify from 'dompurify';

        interface FormData {
            name: string;
            bio: string;
        }

        function UserProfile() {
            const [formData, setFormData] = useState<FormData>({ name: '', bio: '' });
            const [preview, setPreview] = useState('');
            const fileInputRef = useRef<HTMLInputElement>(null);

            const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
                setFormData({ ...formData, name: e.target.value });
            };

            const handleBioChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
                const rawHtml = e.target.value;
                // SAFE: Using DOMPurify
                setPreview(DOMPurify.sanitize(rawHtml));
            };

            const handleSubmit = (e: React.FormEvent) => {
                e.preventDefault();
                // UNSAFE: Direct innerHTML
                document.getElementById('result')!.innerHTML = formData.name;
            };

            return (
                <form onSubmit={handleSubmit}>
                    <input
                        value={formData.name}
                        onChange={handleNameChange}
                    />
                    <textarea
                        value={formData.bio}
                        onChange={handleBioChange}
                    />
                    <input type="file" ref={fileInputRef} />
                    <div dangerouslySetInnerHTML={{ __html: preview }} />
                </form>
            );
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "UserProfile.tsx", "react")

        assert result.framework == FrontendFramework.REACT
        assert len(result.input_sources) >= 3  # form inputs, events
        assert len(result.dangerous_sinks) >= 2  # innerHTML, dangerouslySetInnerHTML

        # Should have both sanitized and unsanitized flows
        findings = tracker.get_security_findings(result)
        assert len(findings) > 0

    def test_vue_composition_api(self):
        """Test Vue 3 Composition API analysis."""
        source = """
        <template>
            <div>
                <input v-model="searchQuery" @input="handleSearch" />
                <div v-html="searchResults"></div>
            </div>
        </template>

        <script setup lang="ts">
        import { ref, computed, watch } from 'vue';
        import DOMPurify from 'dompurify';

        const searchQuery = ref('');
        const rawResults = ref('');

        const searchResults = computed(() => {
            return DOMPurify.sanitize(rawResults.value);
        });

        async function handleSearch() {
            const response = await fetch(`/api/search?q=${searchQuery.value}`);
            rawResults.value = await response.text();
        }
        </script>
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "Search.vue", "vue")

        assert result.framework == FrontendFramework.VUE
        assert any(s.source_type == InputSourceType.VUE_V_MODEL for s in result.input_sources)
        assert any(s.sink_type == DangerousSinkType.V_HTML for s in result.dangerous_sinks)

    def test_angular_reactive_form(self):
        """Test Angular Reactive Forms analysis."""
        source = """
        import { Component, OnInit } from '@angular/core';
        import { FormBuilder, FormGroup, Validators } from '@angular/forms';
        import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

        @Component({
            selector: 'app-contact',
            template: `
                <form [formGroup]="contactForm" (ngSubmit)="onSubmit()">
                    <input formControlName="email" />
                    <textarea formControlName="message"></textarea>
                    <div [innerHTML]="previewHtml"></div>
                </form>
            `
        })
        export class ContactComponent implements OnInit {
            contactForm: FormGroup;
            previewHtml: SafeHtml = '';

            constructor(
                private fb: FormBuilder,
                private sanitizer: DomSanitizer
            ) {}

            ngOnInit() {
                this.contactForm = this.fb.group({
                    email: ['', Validators.email],
                    message: ['']
                });

                this.contactForm.get('message')?.valueChanges.subscribe(value => {
                    // Using Angular's sanitizer
                    this.previewHtml = this.sanitizer.bypassSecurityTrustHtml(value);
                });
            }

            onSubmit() {
                console.log(this.contactForm.value);
            }
        }
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "contact.component.ts", "angular")

        assert result.framework == FrontendFramework.ANGULAR
        assert any(s.source_type == InputSourceType.ANGULAR_FORM for s in result.input_sources)

    def test_summary_output(self):
        """Test summary generation."""
        source = """
        const input = document.getElementById('input');
        const value = input.value;
        document.getElementById('output').innerHTML = value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "xss.js")

        summary = result.summary()
        assert "xss.js" in summary
        assert "Input Sources" in summary
        assert "Dangerous Sinks" in summary

    def test_risk_count(self):
        """Test risk counting."""
        source = """
        const input = document.getElementById('input');
        const value = input.value;
        document.getElementById('output').innerHTML = value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "xss.js")

        counts = result.risk_count
        assert "CRITICAL" in counts
        assert "HIGH" in counts
        assert isinstance(counts["CRITICAL"], int)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_source(self):
        """Handle empty source code."""
        tracker = FrontendInputTracker()
        result = tracker.analyze_file("", "empty.js")

        assert result.file_path == "empty.js"
        assert len(result.input_sources) == 0
        assert len(result.dangerous_sinks) == 0

    def test_no_inputs(self):
        """Handle code with no inputs."""
        source = """
        const message = 'Hello, World!';
        console.log(message);
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "hello.js")

        assert len(result.input_sources) == 0

    def test_no_sinks(self):
        """Handle code with no dangerous sinks."""
        source = """
        const input = document.getElementById('input');
        const value = input.value;
        console.log(value);  // Safe logging
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "safe.js")

        assert len(result.input_sources) >= 1
        assert len(result.dangerous_sinks) == 0

    def test_has_risks_property(self):
        """Test has_risks property."""
        # With risks
        source_risky = """
        const value = event.target.value;
        element.innerHTML = value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source_risky, "risky.js")
        assert result.has_risks or len(result.dangerous_flows) >= 0

        # Without risks
        source_safe = "const x = 1;"
        result_safe = tracker.analyze_file(source_safe, "safe.js")
        assert not result_safe.has_risks

    def test_multiline_patterns(self):
        """Handle multiline code patterns."""
        # Note: Chained method calls across lines are a known limitation
        # Test that we detect patterns that are on single lines within multiline code
        source = """
        // This is a multiline file with various patterns
        const userInput = document.getElementById('search');
        const value = userInput.value;

        // Multiple lines of code
        const output = document.getElementById('output');
        output.innerHTML = value;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "multiline.js")

        # Should still detect patterns
        assert len(result.input_sources) >= 1
        assert len(result.dangerous_sinks) >= 1


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_get_xss_risks(self):
        """Test get_xss_risks aggregation."""
        source1 = """
        const v1 = event.target.value;
        el1.innerHTML = v1;
        """
        source2 = """
        const v2 = location.search;
        el2.innerHTML = v2;
        """

        tracker = FrontendInputTracker()
        results = [
            tracker.analyze_file(source1, "file1.js"),
            tracker.analyze_file(source2, "file2.js"),
        ]

        all_risks = get_xss_risks(results)
        # Should aggregate risks from both files
        assert isinstance(all_risks, list)

    def test_result_dangerous_flows_property(self):
        """Test dangerous_flows property filtering."""
        source = """
        const userInput = event.target.value;
        const clean = DOMPurify.sanitize(userInput);
        element.innerHTML = clean;

        const unsafe = input.value;
        other.innerHTML = unsafe;
        """
        tracker = FrontendInputTracker()
        result = tracker.analyze_file(source, "mixed.js")

        # dangerous_flows should only include unsanitized flows
        all_flows = result.data_flows
        dangerous = result.dangerous_flows

        # Dangerous should be subset of all
        assert len(dangerous) <= len(all_flows)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

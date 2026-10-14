package edu.vit.plantdisease.controller;

import edu.vit.plantdisease.service.AiServiceClient;
import edu.vit.plantdisease.service.DiagnosisService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DiagnosisController.class)
@Import(ApiExceptionHandler.class)
class DiagnosisControllerTest {
    private static final String SESSION_ID = "2af2d828-8d23-4f3c-8e19-92d70a48d97b";

    @Autowired
    private MockMvc mvc;

    @MockBean
    private DiagnosisService diagnoses;

    @MockBean
    private AiServiceClient ai;

    @Test
    void healthReportsAiServiceStatus() throws Exception {
        given(ai.health()).willReturn(Map.of("status", "ok"));

        mvc.perform(get("/api/health"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ok"))
            .andExpect(jsonPath("$.aiService").value("ok"));
    }

    @Test
    void historyRejectsMalformedSessionId() throws Exception {
        mvc.perform(get("/api/diagnoses").header("X-Session-Id", "not-a-uuid"))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.error").value("X-Session-Id must be a UUID."));
    }

    @Test
    void followUpDelegatesUsingValidatedSessionAndDiagnosis() throws Exception {
        UUID diagnosisId = UUID.fromString("5d1f7cf8-b414-4bdf-8a4b-7099a13efc20");
        given(diagnoses.ask(SESSION_ID, diagnosisId, "What should I do next?"))
            .willReturn(Map.of(
                "sender", "assistant",
                "message", "No verified reference is available.",
                "timestamp", Instant.parse("2026-10-14T12:00:00Z"),
                "sources", List.of()
            ));

        mvc.perform(post("/api/diagnoses/{id}/messages", diagnosisId)
                .header("X-Session-Id", SESSION_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"message\":\"What should I do next?\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.sender").value("assistant"))
            .andExpect(jsonPath("$.message").value("No verified reference is available."));

        verify(diagnoses).ask(SESSION_ID, diagnosisId, "What should I do next?");
    }
}

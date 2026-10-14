package edu.vit.plantdisease.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.client.RestTemplate;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@Component
public class AiServiceClient {
    private final RestClient client;
    private final String baseUrl;
    private final RestTemplate multipartClient;
    private final ObjectMapper json;
    public AiServiceClient(@Value("${app.ai-service-url}") String baseUrl, ObjectMapper json) {
        this.baseUrl = baseUrl;
        this.json = json;
        this.client = RestClient.builder().baseUrl(baseUrl).build();
        this.multipartClient = new RestTemplate();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> health() {
        try { return client.get().uri("/health").retrieve().body(Map.class); }
        catch (RestClientException error) {
            throw new AiServiceUnavailableException("The AI service is not reachable.", error);
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> diagnose(byte[] image, String filename, MediaType contentType) {
        ByteArrayResource resource = new ByteArrayResource(image) {
            @Override public String getFilename() { return filename; }
        };
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        HttpHeaders partHeaders = new HttpHeaders();
        partHeaders.setContentType(contentType);
        body.add("image", new HttpEntity<>(resource, partHeaders));
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        try {
            ResponseEntity<Map<String, Object>> response = multipartClient.exchange(
                baseUrl + "/diagnose", org.springframework.http.HttpMethod.POST,
                new HttpEntity<>(body, headers), new ParameterizedTypeReference<>() {});
            return response.getBody();
        } catch (RestClientResponseException error) {
            if (error.getStatusCode().is5xxServerError())
                throw new AiServiceUnavailableException("The AI advisory service is temporarily unavailable. No diagnosis was saved; please try again shortly.", error);
            throw new AiServiceUnavailableException("AI service rejected the image request (HTTP " + error.getStatusCode().value() + ").", error);
        } catch (RestClientException error) {
            throw new AiServiceUnavailableException("The AI service could not complete this diagnosis.", error);
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> followUp(String advisorySessionId, String question) {
        Map<String, String> payload = Map.of("session_id", advisorySessionId, "question", question);
        final String requestJson;
        try { requestJson = json.writeValueAsString(payload); }
        catch (JsonProcessingException error) { throw new AiServiceUnavailableException("Could not encode the advisory request.", error); }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setAccept(java.util.List.of(MediaType.APPLICATION_JSON));
            ResponseEntity<Map<String, Object>> response = multipartClient.exchange(
                baseUrl + "/follow-up", org.springframework.http.HttpMethod.POST,
                new HttpEntity<>(requestJson.getBytes(StandardCharsets.UTF_8), headers),
                new ParameterizedTypeReference<>() {});
            return response.getBody();
        } catch (RestClientResponseException error) {
            throw new AiServiceUnavailableException("The advisory service could not continue this thread. Please try again.", error);
        } catch (RestClientException error) {
            throw new AiServiceUnavailableException("The advisory service could not continue this thread. Please try again.", error);
        }
    }
}

package edu.vit.plantdisease.model;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "chat_messages", indexes = @Index(name = "idx_chat_diagnosis_time", columnList = "diagnosis_id,timestamp"))
public class ChatMessage {
    @Id @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "diagnosis_id", nullable = false)
    private Diagnosis diagnosis;
    @Column(nullable = false, length = 16)
    private String sender;
    @Column(nullable = false, columnDefinition = "TEXT")
    private String message;
    @Column(nullable = false, updatable = false)
    private Instant timestamp;

    protected ChatMessage() {}
    public ChatMessage(Diagnosis diagnosis, String sender, String message) {
        this.diagnosis = diagnosis; this.sender = sender; this.message = message; this.timestamp = Instant.now();
    }
    @PrePersist void onCreate() { if (timestamp == null) timestamp = Instant.now(); }
    public UUID getId() { return id; }
    public Diagnosis getDiagnosis() { return diagnosis; }
    public String getSender() { return sender; }
    public String getMessage() { return message; }
    public Instant getTimestamp() { return timestamp; }
}

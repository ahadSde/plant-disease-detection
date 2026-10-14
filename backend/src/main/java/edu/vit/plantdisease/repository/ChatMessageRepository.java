package edu.vit.plantdisease.repository;

import edu.vit.plantdisease.model.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, UUID> {
    List<ChatMessage> findAllByDiagnosisIdOrderByTimestampAsc(UUID diagnosisId);
}

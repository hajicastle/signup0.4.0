import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import "../styles/NewInvite.css";
import BackIcon from "../assets/backIcon.svg";
import CloseIcon from "../assets/closeIcon.svg";
import CopyIcon from "../assets/copyIcon.svg";

function NewInvite() {
  const [name, setName] = useState("");
  const [links, setLinks] = useState([]);
  const [linkToRemove, setLinkToRemove] = useState(null);
  const [createdLink, setCreatedLink] = useState(null);

  const [invitesLeft, setInvitesLeft] = useState(0);
  const [inviteGenerated, setInviteGenerated] = useState(false);
  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [copyMessage, setCopyMessage] = useState("");

  const navigate = useNavigate();

  const goBack = () => {
    navigate("/");
  };

  // 백엔드에서 유저의 link를 가져오는 메소드
  const fetchLinks = async () => {
    try {
      const response = await api.get("/api/invitation-links/");
      const sortedLinks = response.data.sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      setLinks(sortedLinks);
      setInvitesLeft(5 - sortedLinks.length);
      console.log(sortedLinks);
    } catch (error) {
      console.error("Failed to fetch invite links:", error);
    }
  };

  // 화면 구성 시에 link 가져오기
  useEffect(() => {
    fetchLinks();
  }, []);

  useEffect(() => {
    if (copyMessage) {
      const timer = setTimeout(() => setCopyMessage(""), 2000);
      return () => clearTimeout(timer);
    }
  }, [copyMessage]);

  const handleNameChange = (e) => {
    setName(e.target.value);
  };

  const handleGenerateLink = async () => {
    if (name.trim() !== "" && invitesLeft > 0) {
      try {
        const response = await api.post("/api/create-invitation-link/", {
          name,
        });
        const newLink = {
          invitee_name: name,
          inviter_name: response.data.inviter_name,
          link: response.data.link,
          id: response.data.id,
          created_at: response.data.created_at,
        }; // ID와 이름을 포함하여 newLink 객체 생성
        setName(""); // 입력 필드를 초기화
        fetchLinks(); // 추가된 링크로 데이터 베이스에서 다시 받아오기.
        setCreatedLink(newLink);
        setInviteGenerated(true);
      } catch (error) {
        console.error("Failed to generate invite link:", error);
        console.log("Error response data:", error.response.data);
      }
    } else {
      alert("Please enter a name.");
    }
  };

  const handleCloseModal = () => {
    setInviteGenerated(false);
  };

  const handleCopyLink = (link) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(link)
        .then(() => {
          const userAgent =
            navigator.userAgent || navigator.vendor || window.opera;
          // 안드로이드 환경인지 체크
          const isAndroid = /android/i.test(userAgent);
          // 안드로이드가 아닌 경우에만 메시지 출력
          if (!isAndroid) {
            setCopyMessage("링크가 복사되었습니다.");
          }
        })
        .catch((err) => {
          console.error("Failed to copy: ", err);
        });
    } else {
      alert("복사를 지원하지 않는 환경입니다.");
    }
  };

  const handleRevokeInvite = (linkObj) => {
    setLinkToRemove(linkObj);
    setShowRevokeModal(true);
  };

  const confirmRevokeInvite = async () => {
    try {
      await api.delete(`/api/delete-invitation-link/${linkToRemove.id}/`); // linkToRemove.id 사용
      fetchLinks();
      setShowRevokeModal(false);
      setLinkToRemove(null);
    } catch (error) {
      console.error("Failed to delete invite link:", error);
    }
  };

  const closeRevokeModal = () => {
    setShowRevokeModal(false);
    setLinkToRemove(null);
  };

  const getExpiredDate = (linkObj) => {
    const createdDate = new Date(linkObj.created_at);
    // linkObj.created_at이 Date 객체라고 가정
    const expiredDate = new Date(
      createdDate.getTime() + 7 * 24 * 60 * 60 * 1000
    );
    return expiredDate.toLocaleDateString();
  };

  const getExpiredDateFromCurrentDate = () => {
    const currentDate = new Date();
    // linkObj.created_at이 Date 객체라고 가정
    const expiredDate = new Date(
      currentDate.getTime() + 7 * 24 * 60 * 60 * 1000
    );
    return expiredDate.toLocaleDateString();
  };

  return (
    <div className="container">
      <header className="header">
        <img
          src={BackIcon}
          alt="뒤로가기 아이콘"
          className="back-icon"
          onClick={goBack}
        />
        <div className="header-content">
          <div className="title-container">
            <h1 className="title">초대하기</h1>
            <span className="subtitle">
              팀블은 초대를 통해서만 가입할 수 있어요.
              <br />
              실력있는 지인들을 초대해 함께 해 보세요.
            </span>
          </div>
          <div className="remaining-invites">
            <span className="remaining-text">남은 횟수</span>
            <div className="count-box">
              <span className="count-number">{invitesLeft}</span>
              <span className="count-unit">회</span>
            </div>
          </div>
        </div>
      </header>
      <div className="invite-form">
        <input
          type="text"
          placeholder="이름 입력"
          className="name-input"
          value={name}
          onChange={handleNameChange}
        />
        <button
          className={`generate-link ${name ? "active" : ""}`}
          onClick={handleGenerateLink}
          disabled={!name}
        >
          개인 초대 링크 생성
        </button>
      </div>
      <h2 className="invite-status-title">초대 현황</h2>
      {links.length > 0 ? (
        links.map((linkObj, index) => {
          const expiredDate = getExpiredDate(linkObj);

          const currentTime = new Date();
          const isExpired = currentTime > expiredDate;

          return (
            <div className="invite-status" key={index}>
              <div className="invite-card">
                <div className="invite-card-header">
                  <p className="invitee-name">{linkObj.invitee_name}</p>
                  <button
                    className="revoke-invite-button"
                    onClick={() => handleRevokeInvite(linkObj)}
                  >
                    초대 회수
                  </button>
                </div>
                <div className="expiration-container">
                  <div className="expiration-info">
                    <p className="expiration-title">링크 유효 기간</p>
                    <p className="expiration-date">{expiredDate}</p>
                  </div>
                  <button
                    className={`copy-link-button ${
                      isExpired ? "disabled" : ""
                    }`}
                    onClick={() => !isExpired && handleCopyLink(linkObj.link)}
                    disabled={isExpired}
                  >
                    <img
                      src={CopyIcon}
                      alt="복사 아이콘"
                      className="copy-icon"
                    />
                    <p className="copy-link-title">링크 복사</p>
                  </button>
                </div>
              </div>
            </div>
          );
        })
      ) : (
        <div className="init-invite-status">
          <p>아직 초대한 사람이 없네요!</p>
          <p>주위를 둘러보며 팀블에 함께할 지인을 찾아보세요.</p>
        </div>
      )}

      {showRevokeModal && (
        <div className="modal-overlay">
          <div className="del-modal-content">
            <p className="modal-title">초대를 회수할까요?</p>
            <p className="modal-description">
              초대를 회수하면 차감된
              <br />
              초대 횟수가 다시 반환됩니다.
            </p>
            <div className="modal-buttons">
              <button
                className="modal-button cancel-button"
                onClick={closeRevokeModal}
              >
                취소
              </button>
              <button
                className="modal-button confirm-button"
                onClick={confirmRevokeInvite}
              >
                회수
              </button>
            </div>
          </div>
        </div>
      )}

      {inviteGenerated && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button className="close-modal-button" onClick={handleCloseModal}>
              <img src={CloseIcon} alt="닫기" />
            </button>
            <p className="modal-title">
              초대 링크가 생성되었습니다.
              <br />
              링크를 복사해 초대 상대에게 공유해 주세요.
            </p>
            <hr className="modal-divider" />
            <p className="invitee-name">{createdLink.invitee_name}</p>
            <div className="expiration-container">
              <div className="expiration-info">
                <p className="expiration-title">링크 유효 기간</p>
                <p className="expiration-date">
                  {getExpiredDateFromCurrentDate()}
                </p>
              </div>
              <button
                className="copy-link-button"
                onClick={() => handleCopyLink(createdLink.link)}
              >
                <img src={CopyIcon} alt="복사 아이콘" className="copy-icon" />
                <p className="copy-link-title">링크 복사</p>
              </button>
            </div>
          </div>
        </div>
      )}

      {copyMessage && <div className="copy-message">{copyMessage}</div>}
    </div>
  );
}

export default NewInvite;

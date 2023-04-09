import { Modal as BootstrapModal } from "bootstrap"
import React from "react"
import * as ReactDOMClient from "react-dom/client"
import { io, Socket } from "socket.io-client"

interface Chat {
	id: string
	name: string
	meetingTime: number
	meetingDuration: number
	formatedMeetingDuration: string
	voteCount: number
	voted: boolean
}

interface Message {
	id: string
	chatID: string
	userID: string
	userFirstName: string
	userLastName: string
	content: string
	timestamp: number
}

interface User {
	id: string
	username: string
	firstName: string
	lastName: string
}

function getChatMeetingStartingDate(chat: Chat) {
	const hour = Math.floor(chat.meetingTime / 60 / 60)
	const minute = Math.floor(chat.meetingTime / 60 - hour * 60)
	const second = Math.floor(chat.meetingTime - hour * 60 * 60 - minute * 60)

	const now = new Date()
	const potential = new Date(
		now.getFullYear(),
		now.getMonth(),
		now.getDate(),
		hour,
		minute,
		second
	)

	if (potential.getTime() + chat.meetingDuration * 1000 < now.getTime()) {
		return new Date(potential.getTime() + 1000 * 60 * 60 * 24)
	}

	return potential
}

function getChatRemainingTime(chat: Chat): number {
	const startingDate = getChatMeetingStartingDate(chat)
	const endingTimestamp = startingDate.getTime() / 1000 + chat.meetingDuration

	return endingTimestamp - Date.now() / 1000
}

const MyUserContext = React.createContext<User>(null)

function App() {
	const [selectedChat, setSelectedChat] = React.useState<Chat>()
	const [myUser, setMyUser] = React.useState<User>(null)

	React.useEffect(() => {
		fetch("/users/me").then(response => response.json()).then((json: User) => setMyUser(json))
	}, [])

	if (myUser == null) {
		return <></>
	}

	return <MyUserContext.Provider value={myUser}>
		<div className="d-flex flex-row">
			<ChatList
				selectedChat={selectedChat}
				onChangeChat={chat => setSelectedChat(chat)}/>

			<MessagePane chat={selectedChat}/>
		</div>
	</MyUserContext.Provider>
}

function ChatList(props: {selectedChat?: Chat, onChangeChat: (chat: Chat) => void}) {
	const [chats, setChats] = React.useState<Chat[]>([]);
	const [showProposalModal, setShowProposalModal] = React.useState(false)

	function createChat(name: string) {
		fetch("/chats", {
			method: "POST",
			body: JSON.stringify(name),
			headers: {
				"Content-Type": "application/json"
			}
		}).then(response => response.json()).then((json: Chat) => {
			setChats(chats => [...chats, json])
		})

		setShowProposalModal(false)
	}

	function toggleChatVote(chat: Chat, i: number, toggled: boolean) {
		fetch(`/chats/${chat.id}/vote`, {
			method: toggled ? "POST" : "DELETE"
		})

		const newChat = {...chat}

		newChat.voteCount += toggled ? 1 : -1
		newChat.voted = toggled

		const newChats = [...chats]

		newChats[i] = newChat

		setChats(newChats)

		if (chat.id == props.selectedChat?.id) {
			props.onChangeChat(newChat)
		}
	}

	React.useEffect(() => {
		fetch("/chats").then(response => response.json()).then((json: Chat[]) => setChats(json))
	}, [])

	return <div className="chat-list border-end vh-100">
		<div className="d-flex align-items-center">
			<h1 className="title flex-grow-1 m-3">Nandemo</h1>
			<button type="button"
				className="btn btn-primary d-flex m-3 p-2 shadow"
				onClick={() => setShowProposalModal(true)}>
				<span className="material-symbols-outlined">add</span>
			</button>
		</div>

		<table className="table table-hover">
			<tbody>
				{chats.map((chat, i) => {
					const formattedMeetingTime = Intl.DateTimeFormat("en-US", {
						timeStyle: "short"
					}).format(getChatMeetingStartingDate(chat))

					return <tr
						className={`chat-button${props.selectedChat?.id == chat.id ? " chat-button-selected" : ""}${i == 0 ? " border-top" : ""}`}
						onClick={() => props.onChangeChat(chat)}
						key={chat.id}>
						<td>
							<ToggleableButton
								toggled={chat.voted}
								onToggle={toggled => toggleChatVote(chat, i, toggled)}>
								<button type="button" className="btn btn-outline-secondary">
									{chat.voteCount}
								</button>
							</ToggleableButton>
						</td>

						<td>{chat.name}</td>
						<td>at {formattedMeetingTime}</td>
						<td>for {chat.formatedMeetingDuration}</td>
					</tr>
				})}
			</tbody>
		</table>

		<ChatProposalModal
			shown={showProposalModal}
			onClose={() => setShowProposalModal(false)}
			onSubmit={name => createChat(name)}/>
	</div>
}

function ChatProposalModal(props: {
	shown: boolean,
	onClose: () => void,
	onSubmit: (name: string) => void
}) {
	const nameInputRef = React.useRef<HTMLInputElement>(null)

	function handleSubmission(event: React.FormEvent<HTMLFormElement>) {
		props.onSubmit(nameInputRef.current.value)

		event.preventDefault();
	}

	return <Modal shown={props.shown} onClose={() => props.onClose()}>
		<div className="modal" tabIndex={-1}>
			<div className="modal-dialog">
				<div className="modal-content border-0">
					<div className="modal-header">
						<h4 className="modal-title fw-bold">Propose a Chat</h4>
						<button type="button"
							className="btn-close"
							onClick={() => props.onClose()}/>
					</div>

					<form onSubmit={event => handleSubmission(event)}>
						<div className="modal-body">
							<input type="text"
								className="form-control"
								placeholder="Enter the name of your chat"
								required
								ref={nameInputRef}/>
						</div>

						<div className="modal-footer">
							<button type="button"
								className="btn btn-secondary"
								onClick={() => props.onClose()}>Close</button>

							<button type="submit" className="btn btn-primary">Create</button>
						</div>
					</form>
				</div>
			</div>
		</div>
	</Modal>
}

function Countdown(props: {chat: Chat}) {
	const [intervalID, setIntervalID] = React.useState<NodeJS.Timer>(null)
	const [_, setPseudoState] = React.useState(false)

	React.useEffect(() => {
		setIntervalID(setInterval(() => setPseudoState(pseudoState => !pseudoState)))

		return () => clearInterval(intervalID)
	}, [])

	const remaining = getChatRemainingTime(props.chat)
	const hoursRemaining = Math.floor(remaining / 60 / 60)
	const minutesRemaining = Math.floor(remaining / 60 - hoursRemaining * 60)
	const secondsRemaining =
		Math.floor(remaining - hoursRemaining * 60 * 60 - minutesRemaining * 60)
			.toString()
			.padStart(2, "0")

	return <span className={`countdown fw-bold position-absolute px-3 py-2 shadow text-white ${remaining > props.chat.meetingDuration ? "bg-secondary" : "bg-primary"}`}>
		{`${hoursRemaining}:${minutesRemaining}:${secondsRemaining}`}
	</span>
}

function MessageComponent(props: {message: Message}) {
	const myUser = React.useContext(MyUserContext)

	const sentTime = new Date(props.message.timestamp * 1000)
	const formattedDate = new Intl.DateTimeFormat("en-US").format(sentTime)
	const formattedTime = new Intl.DateTimeFormat("en-US", {
		timeStyle: "short"
	}).format(sentTime)

	return (
		<div className={`d-flex flex-column mb-2 ${props.message.userID == myUser.id ? "align-items-end align-self-end" : "align-items-start align-self-start"}`}>
			<span className={`message-content bg-primary mb-1 shadow-md text-light ${props.message.userID == myUser.id ? "message-content-right" : "message-content-left"}`}>
				{props.message.content}
			</span>

			<span className="message-metadatum d-block text-secondary">
				{`${props.message.userFirstName} ${props.message.userLastName}`}
			</span>

			<span className="message-metadatum d-block text-secondary mb-1">
				{`${formattedDate}, ${formattedTime}`}
			</span>
		</div>
	)
}

function MessagePane(props: {chat?: Chat}) {
	const messageContainerRef = React.useRef<HTMLDivElement>(null);
	const messageInputRef = React.useRef<HTMLInputElement>(null)
	const [messages, setMessages] = React.useState<Message[]>([]);
	const [_, setPseudoState] = React.useState(false);
	const [socket, setSocket] = React.useState<Socket>(null)

	function sendMessage() {
		if (messageContainerRef.current == null || messageInputRef.current == null || socket == null) {
			return;
		}

		socket.emit("message", messageInputRef.current.value)

		messageInputRef.current.value = ""
	}

	React.useEffect(() => {
		if (props.chat == undefined) {
			setMessages([])

			return () => {}
		}

		fetch(`/chats/${props.chat.id}/messages`)
			.then(response => response.json())
			.then((json: Message[]) => setMessages(json))

		const socket = io({
			auth: {
				chatID: props.chat.id
			}
		})

		socket.on("message_broadcast", (message: Message) => {
			setMessages(messages => [...messages, message])
		})

		setSocket(socket)

		return () => socket.disconnect()
	}, [props.chat])

	React.useEffect(() => {
		if (messageContainerRef.current != null) {
			messageContainerRef.current.scrollTop = messageContainerRef.current.offsetHeight
		}
	}, [messages])

	if (props.chat == undefined) {
		return <></>
	}

	const isChatMeetingOngoing = getChatRemainingTime(props.chat) > props.chat.meetingDuration
	const isChatDisabled = isChatMeetingOngoing || !props.chat.voted || props.chat.voteCount < 2

	return <div className="d-flex flex-column flex-grow-1 vh-100">
		<div
			className="message-container d-flex flex-column flex-grow-1 overflow-scroll px-4 pb-3"
			ref={messageContainerRef}>
			{messages.map(message => <MessageComponent key={message.id} message={message}/>)}
		</div>

		<div className="border-top d-flex p-3 shadow-sm">
			<input type="text"
				key={props.chat.id}
				className="new-message-input form-control rounded-0 rounded-start"
				placeholder={props.chat.voted ? "Enter your message" : "Vote for this chat to enter a message"}
				disabled={isChatDisabled}
				onInput={() => setPseudoState(pseudoState => !pseudoState)}
				ref={messageInputRef}/>

			<button type="button"
				className="new-message-button btn btn-primary d-flex rounded-0 rounded-end"
				disabled={isChatDisabled|| !messageInputRef.current?.value?.length}
				onClick={() => sendMessage()}>
				<span className="material-symbols-outlined">send</span>
			</button>
		</div>

		<Countdown chat={props.chat}/>
	</div>
}

function Modal(props: {children: JSX.Element, shown: boolean, onClose: () => void}) {
	const childrenRef = React.useRef<HTMLElement>(null)
	const [modal, setModal] = React.useState<BootstrapModal>(null)

	React.useEffect(() => {
		setModal(new BootstrapModal(childrenRef.current))
	}, [])

	React.useEffect(() => {
		if (modal != null) {
			if (props.shown) {
				modal.show()
			} else {
				modal.hide()
			}
		}
	}, [props.shown])

	return React.cloneElement(props.children, {
		ref: childrenRef
	})
}

function ToggleableButton(props: {
	children: JSX.Element,
	toggled: boolean,
	onToggle: (toggled: boolean) => void
}) {
	return React.cloneElement(props.children, {
		className: (props.children.props.className ?? "") + (props.toggled ? " active" : ""),
		onClick: (event: Event) => {
			props.onToggle(!props.toggled)

			event.stopPropagation()
		}
	})
}

ReactDOMClient
	.createRoot(document.querySelector(".root"))
	.render(<App/>)

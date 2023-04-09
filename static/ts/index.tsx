import React from "react"
import * as ReactDOMClient from "react-dom/client"
import { io, Socket } from "socket.io-client"

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

const MyUserContext = React.createContext<User>(null)

function App() {
	const [myUser, setMyUser] = React.useState<User>(null)

	React.useEffect(() => {
		fetch("/users/me").then(response => response.json()).then((json: User) => setMyUser(json))
	}, [])

	if (myUser == null) {
		return <></>
	}

	return <MyUserContext.Provider value={myUser}>
		<MessagePane chatID="4f35714b-171e-45f9-bf2e-6a92cdfb6f72"></MessagePane>
	</MyUserContext.Provider>
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

function MessagePane(props: {chatID?: string}) {
	const messageContainerRef = React.useRef<HTMLDivElement>(null);
	const messageInputRef = React.useRef<HTMLInputElement>(null)
	const [messages, setMessages] = React.useState<Message[]>([]);
	const [_, setPseudoState] = React.useState(false);
	const [socket, setSocket] = React.useState<Socket>(null)

	function sendMessage() {
		if (messageContainerRef == null || messageInputRef == null || socket == null) {
			return;
		}

		socket.emit("message", messageInputRef.current.value)

		messageInputRef.current.value = ""
	}

	React.useEffect(() => {
		if (props.chatID == undefined) {
			setMessages([])

			return () => {}
		}

		fetch(`/chats/${props.chatID}/messages`)
			.then(response => response.json())
			.then((json: Message[]) => setMessages(json))

		const socket = io({
			auth: {
				chatID: props.chatID
			}
		})

		socket.on("message_broadcast", (message: Message) => {
			setMessages(messages => [...messages, message])
		})

		setSocket(socket)

		return () => socket.disconnect()
	}, [props.chatID])

	React.useEffect(() => {
		messageContainerRef.current.scrollTop = messageContainerRef.current.offsetHeight
	}, [messages])

	if (props.chatID == undefined) {
		return <></>
	}

	return <div className="d-flex flex-column vh-100">
		<div
			className="d-flex flex-column flex-grow-1 overflow-scroll p-2"
			ref={messageContainerRef}>
			{messages.map(message =>
				<MessageComponent key={message.id} message={message}></MessageComponent>
			)}
		</div>

		<div className="border-top d-flex p-3 shadow-sm">
			<input type="text"
				className="new-message-input form-control rounded-0 rounded-start"
				placeholder="Enter your message"
				onInput={() => setPseudoState(pseudoState => !pseudoState)}
				ref={messageInputRef}></input>

			<button type="button"
				className="new-message-button btn btn-primary d-flex rounded-0 rounded-end"
				onClick={() => sendMessage()}
				disabled={!messageInputRef.current?.value?.length}>
				<span className="material-symbols-outlined">send</span>
			</button>
		</div>
	</div>
}

ReactDOMClient
	.createRoot(document.querySelector(".root"))
	.render(<App></App>)

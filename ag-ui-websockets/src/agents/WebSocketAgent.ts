import { AbstractAgent, RunAgentInput, BaseEvent } from "@ag-ui/client"
import { Observable } from "rxjs"

export class WebSocketAgent extends AbstractAgent {
  private websocket: WebSocket | null = null
  private websocketUrl: string

  constructor(websocketUrl: string = "ws://localhost:8765") {
    super()
    this.websocketUrl = websocketUrl
  }

  private ensureConnection(): Promise<WebSocket> {
    return new Promise((resolve, reject) => {
      if (this.websocket?.readyState === WebSocket.OPEN) {
        resolve(this.websocket)
        return
      }

      this.websocket = new WebSocket(this.websocketUrl)
      
      this.websocket.onopen = () => {
        console.log('WebSocket connected to', this.websocketUrl)
        resolve(this.websocket!)
      }

      this.websocket.onerror = (error) => {
        console.error('WebSocket connection error:', error)
        reject(error)
      }

      // Set a connection timeout
      setTimeout(() => {
        if (this.websocket?.readyState !== WebSocket.OPEN) {
          reject(new Error('WebSocket connection timeout'))
        }
      }, 5000)
    })
  }

  protected run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable<BaseEvent>((observer) => {
      const connectAndRun = async () => {
        try {
          const ws = await this.ensureConnection()

          // Send the input via WebSocket
          ws.send(JSON.stringify(input))
          console.log('Sent input to WebSocket:', input)

          // Listen for events from WebSocket
          ws.onmessage = (event) => {
            try {
              const agentEvent = JSON.parse(event.data) as BaseEvent
              console.log('Received event:', agentEvent)
              observer.next(agentEvent)
            } catch (error) {
              console.error('Error parsing WebSocket message:', error)
              observer.error(error)
            }
          }

          ws.onerror = (error) => {
            console.error('WebSocket error during run:', error)
            observer.error(error)
          }

          ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason)
            if (event.code !== 1000) {
              observer.error(new Error(`WebSocket closed with code ${event.code}: ${event.reason}`))
            } else {
              observer.complete()
            }
          }

        } catch (error) {
          console.error('Failed to connect to WebSocket:', error)
          observer.error(error)
        }
      }

      connectAndRun()

      // Cleanup function
      return () => {
        if (this.websocket?.readyState === WebSocket.OPEN) {
          this.websocket.close(1000, 'Observable unsubscribed')
        }
      }
    })
  }

  public disconnect(): void {
    if (this.websocket) {
      this.websocket.close(1000, 'Manually disconnected')
      this.websocket = null
    }
  }

  public isConnected(): boolean {
    return this.websocket?.readyState === WebSocket.OPEN
  }
} 
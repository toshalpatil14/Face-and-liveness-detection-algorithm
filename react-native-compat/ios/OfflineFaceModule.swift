import Foundation

@objc(OfflineFaceModule)
class OfflineFaceModule: NSObject {
  @objc
  static func requiresMainQueueSetup() -> Bool {
    return false
  }

  @objc(initializeModels:rejecter:)
  func initializeModels(resolve: RCTPromiseResolveBlock, reject: RCTPromiseRejectBlock) {
    // Load ONNX assets from the iOS app bundle models directory.
    resolve(nil)
  }

  @objc(getModelProfile:rejecter:)
  func getModelProfile(resolve: RCTPromiseResolveBlock, reject: RCTPromiseRejectBlock) {
    reject("NOT_WIRED", "Native ONNX runtime wiring is pending.", nil)
  }

  @objc(registerFace:frameBase64:resolver:rejecter:)
  func registerFace(
    name: String,
    frameBase64: String,
    resolve: RCTPromiseResolveBlock,
    reject: RCTPromiseRejectBlock
  ) {
    reject("NOT_WIRED", "Native ONNX runtime wiring is pending.", nil)
  }

  @objc(verifyFace:requireActiveChallenge:resolver:rejecter:)
  func verifyFace(
    frameBase64: String,
    requireActiveChallenge: Bool,
    resolve: RCTPromiseResolveBlock,
    reject: RCTPromiseRejectBlock
  ) {
    reject("NOT_WIRED", "Native ONNX runtime wiring is pending.", nil)
  }

  @objc(getPendingEvents:rejecter:)
  func getPendingEvents(resolve: RCTPromiseResolveBlock, reject: RCTPromiseRejectBlock) {
    reject("NOT_WIRED", "Local mobile event store is pending.", nil)
  }

  @objc(syncPendingEvents:rejecter:)
  func syncPendingEvents(resolve: RCTPromiseResolveBlock, reject: RCTPromiseRejectBlock) {
    reject("NOT_WIRED", "AWS sync endpoint integration is pending.", nil)
  }

  @objc(purgeSyncedEvents:rejecter:)
  func purgeSyncedEvents(resolve: RCTPromiseResolveBlock, reject: RCTPromiseRejectBlock) {
    reject("NOT_WIRED", "Purge integration is pending.", nil)
  }
}

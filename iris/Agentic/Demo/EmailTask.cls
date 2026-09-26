Class Agentic.Demo.EmailTask Extends %SYS.Task.Definition
{

Parameter TaskName = "Agentic simulated operational email";

Property Recipient As %String(MAXLEN = 320) [ InitialExpression = "dba@example.test" ];

Property Subject As %String(MAXLEN = 240) [ InitialExpression = "IRIS operational status" ];

Property CpuSummary As %String(MAXLEN = 4000);

Property LockSummary As %String(MAXLEN = 4000);

Property EvidenceIds As %String(MAXLEN = 4000);

ClassMethod SendSimulatedEmail(
    recipient As %String,
    subject As %String,
    cpuSummary As %String,
    lockSummary As %String,
    evidenceIds As %String) As %Status
{
    Set messageId = $Increment(^AgenticDemoEmail("Sequence"))
    Set ^AgenticDemoEmail(messageId, "Recipient") = recipient
    Set ^AgenticDemoEmail(messageId, "Subject") = subject
    Set ^AgenticDemoEmail(messageId, "CpuSummary") = cpuSummary
    Set ^AgenticDemoEmail(messageId, "LockSummary") = lockSummary
    Set ^AgenticDemoEmail(messageId, "EvidenceIds") = evidenceIds
    Set ^AgenticDemoEmail(messageId, "CreatedAt") = $ZDateTime($Horolog, 3, 1, 3)
    Set ^AgenticDemoEmail(messageId, "Delivery") = "SIMULATED"
    Quit $$$OK
}

Method OnTask() As %Status
{
    Quit ..SendSimulatedEmail(
        ..Recipient,
        ..Subject,
        ..CpuSummary,
        ..LockSummary,
        ..EvidenceIds)
}

}

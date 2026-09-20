Class Argus.Collector Extends %SYS.Task.Definition
{
Parameter TaskName = "Argus operational collection";
Parameter RESOURCE = "%Admin_Operate:USE";

Method OnTask() As %Status [ Language = python ]
{
from argus.jobs import collect
collect()
return 1
}
}

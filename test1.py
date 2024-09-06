class Solution:
    def reverseKGroup(self, head: Optional[ListNode], k: int) -> Optional[ListNode]:
        dummy = ListNode(0, head)
        groupPrev = dummy

        while 1:
            kNode = self.getkNode(groupPrev, k)
            if not kNode:
                break
            groupNext = kNode.next

            prev, curr = kNode.next, groupPrev.next
            while curr != groupNext:
                nextNode = curr.next
                curr.next = prev
                prev = curr
                curr = nextNode

            tmp = groupPrev.next
            groupPrev.next = kNode
            groupPrev = tmp 
            
        return dummy.next        
    
    def getkNode(self, curr, k):
        while curr and k > 0:
            curr = curr.next
            k -= 1
        return curr

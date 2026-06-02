import { useState } from 'react'
import { CommentsTable } from '@/components/admin/CommentsTable'
import { PostsTable } from '@/components/admin/PostsTable'

type Tab = 'posts' | 'comments'

const TAB_IDS: Record<Tab, string> = {
  posts: 'tab-posts',
  comments: 'tab-comments',
}

function tabClass(tab: Tab, activeTab: Tab): string {
  return tab === activeTab
    ? 'px-4 py-2 border-b-2 border-blue-600 font-medium text-blue-600'
    : 'px-4 py-2 text-gray-500 hover:text-gray-700'
}

/**
 * Admin content management page with tabbed navigation between Posts and Comments tables.
 * Renders one table at a time based on the active tab selection.
 */
export default function ContentPage() {
  const [activeTab, setActiveTab] = useState<Tab>('posts')

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Content</h1>
      <div role="tablist" className="flex border-b border-gray-200 mb-6">
        <button
          id={TAB_IDS.posts}
          type="button"
          role="tab"
          aria-selected={activeTab === 'posts'}
          onClick={() => setActiveTab('posts')}
          className={tabClass('posts', activeTab)}
        >
          Posts
        </button>
        <button
          id={TAB_IDS.comments}
          type="button"
          role="tab"
          aria-selected={activeTab === 'comments'}
          onClick={() => setActiveTab('comments')}
          className={tabClass('comments', activeTab)}
        >
          Comments
        </button>
      </div>
      <div role="tabpanel" aria-labelledby={TAB_IDS[activeTab]}>
        {activeTab === 'posts' && <PostsTable />}
        {activeTab === 'comments' && <CommentsTable />}
      </div>
    </div>
  )
}

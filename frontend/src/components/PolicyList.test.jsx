import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PolicyList from './PolicyList.jsx'


afterEach(cleanup)


describe('PolicyList', () => {
  it('renders policies and sends the selected filename to every action', () => {
    const actions = {
      onRefresh: vi.fn(),
      onView: vi.fn(),
      onDownload: vi.fn(),
      onHistory: vi.fn(),
      onDelete: vi.fn(),
    }
    render(
      <PolicyList
        tenantId="tenant_A"
        policies={[{ id: 'policy-1', filename: 'demo.cedar' }]}
        busy=""
        {...actions}
      />,
    )

    expect(screen.getByText('demo.cedar')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    fireEvent.click(screen.getByRole('button', { name: 'View' }))
    fireEvent.click(screen.getByRole('button', { name: 'Download' }))
    fireEvent.click(screen.getByRole('button', { name: 'History' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(actions.onRefresh).toHaveBeenCalledOnce()
    expect(actions.onView).toHaveBeenCalledWith('demo.cedar')
    expect(actions.onDownload).toHaveBeenCalledWith('demo.cedar')
    expect(actions.onHistory).toHaveBeenCalledWith('demo.cedar')
    expect(actions.onDelete).toHaveBeenCalledWith('demo.cedar')
  })

  it('shows the empty state when the tenant has no policies', () => {
    render(
      <PolicyList
        tenantId="tenant_A"
        policies={[]}
        busy=""
        onRefresh={() => {}}
        onView={() => {}}
        onDownload={() => {}}
        onHistory={() => {}}
        onDelete={() => {}}
      />,
    )

    expect(screen.getByText('No policies found.')).toBeTruthy()
  })
})

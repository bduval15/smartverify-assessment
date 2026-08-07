import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AccessPanel from './AccessPanel.jsx'


afterEach(cleanup)

const USERS = [
  {
    user_id: 'user_1',
    customer_id: 'customer_1',
    tenant_ids: ['tenant_A'],
  },
  {
    user_id: 'user_2',
    customer_id: 'customer_1',
    tenant_ids: ['tenant_A', 'tenant_B'],
  },
]


describe('AccessPanel', () => {
  it('renders backend-provided customer and tenant access', () => {
    render(
      <AccessPanel
        users={USERS}
        userId="user_2"
        tenantId="tenant_B"
        authorizedTenants={USERS[1].tenant_ids}
        onUserChange={() => {}}
        onTenantChange={() => {}}
      />,
    )

    expect(screen.getByRole('option', { name: 'user_1 (customer_1)' })).toBeTruthy()
    expect(screen.getByRole('option', { name: 'tenant_B' }).selected).toBe(true)
  })

  it('reports user and tenant selections', () => {
    const onUserChange = vi.fn()
    const onTenantChange = vi.fn()
    render(
      <AccessPanel
        users={USERS}
        userId="user_1"
        tenantId="tenant_A"
        authorizedTenants={USERS[0].tenant_ids}
        onUserChange={onUserChange}
        onTenantChange={onTenantChange}
      />,
    )

    fireEvent.change(screen.getByLabelText('User'), {
      target: { value: 'user_2' },
    })
    fireEvent.change(screen.getByLabelText('Tenant'), {
      target: { value: 'tenant_A' },
    })

    expect(onUserChange).toHaveBeenCalledWith('user_2')
    expect(onTenantChange).toHaveBeenCalledWith('tenant_A')
  })
})

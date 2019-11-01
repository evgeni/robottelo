"""Test module for Subscriptions/Manifests UI

:Requirement: Subscription

:CaseAutomation: Automated

:CaseLevel: Component

:CaseComponent: SubscriptionManagement

:TestType: Functional

:CaseImportance: High

:Upstream: No
"""
import pytest
from tempfile import mkstemp

from airgun.session import Session
from fauxfactory import gen_string
from nailgun import entities

from robottelo import manifests
from robottelo.api.utils import create_role_permissions
from robottelo.cli.factory import (
    make_virt_who_config,
    setup_virtual_machine,
    virt_who_hypervisor_config
)
from robottelo.config import settings
from robottelo.constants import (
    DEFAULT_SUBSCRIPTION_NAME,
    DISTRO_RHEL7,
    VDC_SUBSCRIPTION_NAME,
    VIRT_WHO_HYPERVISOR_TYPES,
)
from robottelo.decorators import (
    run_in_one_thread,
    skip_if_not_set,
    setting_is_set,
    tier2,
    tier3,
    upgrade,
)
from robottelo.products import RepositoryCollection, RHELAnsibleEngineRepository
from robottelo.vm import VirtualMachine
import time
pytestmark = [run_in_one_thread]

if not setting_is_set('fake_manifest'):
    pytest.skip('skipping tests due to missing fake_manifest settings', allow_module_level=True)


@tier2
@upgrade
def test_positive_end_to_end(session):
    """Upload a manifest with minimal input parameters, attempt to
    delete it with checking the warning message and hit 'Cancel' button after than delete it.

    :id: 580fc072-01e0-4f83-8cbb-2a8522d76243

    :expectedresults:
        1. The manifest was uploaded successfully.
        2. Manifest import is reflected at the dashboard
        3. When attempting to delete the manifest the confirmation dialog contains informative
            message which warns user about downsides and consequences of manifest deletion.
        4. When hitting cancel the manifest was not deleted.
        5. When deleting and confirming deletion, the manifest was deleted successfully.

    :BZ: 1266827

    :CaseImportance: Critical
    """
    expected_message_lines = [
        'Are you sure you want to delete the manifest?',
        'Note: Deleting a subscription manifest is STRONGLY discouraged. '
        'Deleting a manifest will:',
        'Delete all subscriptions that are attached to running hosts.',
        'Delete all subscriptions attached to activation keys.',
        'Disable Red Hat Insights.',
        'Require you to upload the subscription-manifest and re-attach '
        'subscriptions to hosts and activation keys.',
        'This action should only be taken in extreme circumstances or for '
        'debugging purposes.',
    ]
    org = entities.Organization().create()
    _, temporary_local_manifest_path = mkstemp(prefix='manifest-', suffix='.zip')
    with manifests.clone() as manifest:
        with open(temporary_local_manifest_path, 'wb') as file_handler:
            file_handler.write(manifest.content.read())
    with session:
        session.organization.select(org.name)
        # Ignore "404 Not Found" as server will connect to upstream subscription service to verify
        # the consumer uuid, that will be displayed in flash error messages
        # Note: this happen only when using clone manifest.
        session.subscription.add_manifest(temporary_local_manifest_path,
                                          ignore_error_messages=['404 Not Found'])
        assert session.subscription.has_manifest
        # dashboard check
        subscription_values = session.dashboard.read('SubscriptionStatus')['subscriptions']
        assert subscription_values[0][
            'Subscription Status'] == 'Active Subscriptions'
        assert int(subscription_values[0]['Count']) >= 1
        assert subscription_values[1][
            'Subscription Status'] == 'Subscriptions Expiring in 120 Days'
        assert int(subscription_values[1]['Count']) == 0
        assert subscription_values[2][
            'Subscription Status'] == 'Recently Expired Subscriptions'
        assert int(subscription_values[2]['Count']) == 0
        # manifest delete testing
        delete_message = session.subscription.read_delete_manifest_message()
        assert ' '.join(expected_message_lines) == delete_message
        assert session.subscription.has_manifest
        session.subscription.delete_manifest(ignore_error_messages=['404 Not Found'])
        assert not session.subscription.has_manifest


@tier2
def test_positive_access_with_non_admin_user_without_manifest(test_name):
    """Access subscription page with user that has only view_subscriptions
    permission and organization that has no manifest uploaded.

    :id: dab9dc15-39a8-4105-b7ff-ecef909dc6e6

    :expectedresults: Subscription page is rendered properly without errors

    :BZ: 1417082

    :CaseLevel: Integration

    :CaseImportance: Critical
    """
    org = entities.Organization().create()
    role = entities.Role(organization=[org]).create()
    create_role_permissions(
        role,
        {'Katello::Subscription': ['view_subscriptions']}
    )
    user_password = gen_string('alphanumeric')
    user = entities.User(
        admin=False,
        role=[role],
        password=user_password,
        organization=[org],
        default_organization=org,
    ).create()
    with Session(test_name, user=user.login, password=user_password) as session:
        assert not session.subscription.search('')
        assert not session.subscription.has_manifest


@tier2
@upgrade
def test_positive_access_with_non_admin_user_with_manifest(test_name):
    """Access subscription page with user that has only view_subscriptions
    permission and organization that has a manifest uploaded.

    :id: 9184fcf6-36be-42c8-984c-3c5d7834b3b4

    :expectedresults: Subscription page is rendered properly without errors
        and the default subscription is visible

    :BZ: 1417082, 1651981

    :customerscenario: true

    :CaseLevel: Integration

    :CaseImportance: Critical
    """
    org = entities.Organization().create()
    manifests.upload_manifest_locked(org.id)
    role = entities.Role(organization=[org]).create()
    create_role_permissions(
        role,
        {'Katello::Subscription': ['view_subscriptions']}
    )
    user_password = gen_string('alphanumeric')
    user = entities.User(
        admin=False,
        role=[role],
        password=user_password,
        organization=[org],
        default_organization=org,
    ).create()
    with Session(test_name, user=user.login, password=user_password) as session:
        assert (session.subscription.search(
            'name = "{0}"'.format(DEFAULT_SUBSCRIPTION_NAME))[0]['Name']
                == DEFAULT_SUBSCRIPTION_NAME)


@tier2
def test_positive_access_manifest_as_another_admin_user(test_name):
    """Other admin users should be able to access and manage a manifest
    uploaded by a different admin.

    :id: 02e319da-3b7a-4694-9164-475c2c71b9a8

    :expectedresults: Other admin user should see/manage the manifest

    :BZ: 1669241

    :customerscenario: true

    :CaseLevel: Integration

    :CaseImportance: High
    """
    org = entities.Organization().create()
    user1_password = gen_string('alphanumeric')
    user1 = entities.User(
        admin=True,
        password=user1_password,
        organization=[org],
        default_organization=org,
    ).create()
    user2_password = gen_string('alphanumeric')
    user2 = entities.User(
        admin=True,
        password=user2_password,
        organization=[org],
        default_organization=org,
    ).create()
    # use the first admin to upload a manifest
    with Session(test_name, user=user1.login, password=user1_password) as session:
        manifests.upload_manifest_locked(org.id)
        assert session.subscription.has_manifest
        # store subscriptions that have "Red Hat" in the name for later
        rh_subs = session.subscription.search("Red Hat")
    # try to view and delete the manifest with another admin
    with Session(test_name, user=user2.login, password=user2_password) as session:
        assert session.subscription.has_manifest
        assert rh_subs == session.subscription.search("Red Hat")
        session.subscription.delete_manifest(ignore_error_messages=['404 Not Found'])
        assert not session.subscription.has_manifest


@tier3
def test_positive_view_vdc_subscription_products(session):
    """Ensure that Virtual Datacenters subscription provided products is
    not empty and that a consumed product exist in content products.

    :id: cc4593f0-66ab-4bf6-87d1-d4bd9c89eba5

    :customerscenario: true

    :steps:
        1. Upload a manifest with Virtual Datacenters subscription
        2. Enable a products provided by Virtual Datacenters subscription,
           and synchronize the auto created repository
        3. Create content view with the product repository, and publish it
        4. Create a lifecycle environment and promote the content view to
           it.
        5. Create an activation key with the content view and lifecycle
           environment
        6. Subscribe a host to the activation key
        7. Goto Hosts -> Content hosts and select the created content host
        8. Attach VDC subscription to content host
        9. Goto Content -> Red Hat Subscription
        10. Select Virtual Datacenters subscription

    :expectedresults:
        1. assert that the provided products is not empty
        2. assert that the enabled product is in subscription Product Content

    :BZ: 1366327

    :CaseLevel: System
    """
    org = entities.Organization().create()
    lce = entities.LifecycleEnvironment(organization=org).create()
    repos_collection = RepositoryCollection(
        distro=DISTRO_RHEL7, repositories=[RHELAnsibleEngineRepository(cdn=True)])
    product_name = repos_collection.rh_repos[0].data['product']
    repos_collection.setup_content(
        org.id, lce.id, upload_manifest=True, rh_subscriptions=[DEFAULT_SUBSCRIPTION_NAME])
    with VirtualMachine() as vm:
        setup_virtual_machine(
            vm,
            org.label,
            activation_key=repos_collection.setup_content_data['activation_key']['name'],
            install_katello_agent=False
        )
        with session:
            session.organization.select(org.name)
            session.contenthost.add_subscription(vm.hostname, VDC_SUBSCRIPTION_NAME)
            provided_products = session.subscription.provided_products(VDC_SUBSCRIPTION_NAME)
            # ensure that subscription provided products list is not empty and that the product is
            # in the provided products.
            assert provided_products and product_name in provided_products
            content_products = session.subscription.content_products(VDC_SUBSCRIPTION_NAME)
            # ensure that subscription enabled products list is not empty and that product is in
            # content products.
            assert content_products and product_name in content_products


@skip_if_not_set('compute_resources')
@tier3
def test_positive_view_vdc_guest_subscription_products(session):
    """Ensure that Virtual Data Centers guest subscription Provided
    Products and Content Products are not empty.

    :id: 4a6f6933-8e26-4c47-b544-a300e11a8454

    :customerscenario: true

    :steps:
        1. Upload a manifest with Virtual Datacenters subscription
        2. Config a virtual machine virt-who service for a hypervisor
        3. Ensure virt-who hypervisor host exist
        4. Attach Virtual Datacenters subscription to the virt-who
           hypervisor
        5. Go to Content -> Red Hat Subscription
        6. Select Virtual Datacenters subscription with type Guests of
           virt-who hypervisor

    :expectedresults:
        1. The Virtual Data Centers guests subscription Provided Products
           is not empty and one of the provided products exist
        2. The Virtual Data Centers guests subscription Product Content is
           not empty and one of the consumed products exist

    :BZ: 1395788, 1506636, 1487317

    :CaseLevel: System
    """
    org = entities.Organization().create()
    lce = entities.LifecycleEnvironment(organization=org).create()
    provisioning_server = settings.compute_resources.libvirt_hostname
    rh_product_repository = RHELAnsibleEngineRepository(cdn=True)
    product_name = rh_product_repository.data['product']
    # Create a new virt-who config
    virt_who_config = make_virt_who_config({
        'organization-id': org.id,
        'hypervisor-type': VIRT_WHO_HYPERVISOR_TYPES['libvirt'],
        'hypervisor-server': 'qemu+ssh://{0}/system'.format(provisioning_server),
        'hypervisor-username': 'root',
    })
    # create a virtual machine to host virt-who service
    with VirtualMachine() as virt_who_vm:
        # configure virtual machine and setup virt-who service
        virt_who_data = virt_who_hypervisor_config(
            virt_who_config['general-information']['id'],
            virt_who_vm,
            org_id=org.id,
            lce_id=lce.id,
            hypervisor_hostname=provisioning_server,
            configure_ssh=True,
            subscription_name=VDC_SUBSCRIPTION_NAME,
            extra_repos=[rh_product_repository.data]
        )
        virt_who_hypervisor_host = virt_who_data['virt_who_hypervisor_host']
        with session:
            session.organization.select(org.name)
            # ensure that VDS subscription is assigned to virt-who hypervisor
            content_hosts = session.contenthost.search(
                'subscription_name = "{0}" and name = "{1}"'.format(
                    VDC_SUBSCRIPTION_NAME, virt_who_hypervisor_host['name'])
            )
            assert content_hosts and content_hosts[0]['Name'] == virt_who_hypervisor_host['name']
            # ensure that hypervisor guests subscription provided products list is not empty and
            # that the product is in provided products.
            provided_products = session.subscription.provided_products(
                VDC_SUBSCRIPTION_NAME, virt_who=True)
            assert provided_products and product_name in provided_products
            # ensure that hypervisor guests subscription content products list is not empty and
            # that product is in content products.
            content_products = session.subscription.content_products(
                VDC_SUBSCRIPTION_NAME, virt_who=True)
            assert content_products and product_name in content_products


@tier3
def test_select_customizable_columns_uncheck_and_checks_all_checkboxes(session):
    """Ensures that no column headers from checkboxes show up in the table after
    unticking everything from selectable customizable column

    :id: 88e140c7-ab4b-4d85-85bd-d3eff12162d7

    :steps:
        1. Login and go to Content -> Subscription
        2. Click selectable customizable column icon next to search button
        3. Iterate through list of checkboxes
        4. Unchecks all ticked checkboxes
        5. Verify that the table header column doesn't have any headers from
           checkboxes

        Note: Table header will always contain 'Select all rows' header in html,
        but will not be displayed in UI

    :expectedresults:
        1. No column headers show up

    :CaseImportance: Medium
    """
    checkbox_dict = {
        'Name': False,
        'Type': False,
        'SKU': False,
        'Contract': False,
        'Start Date': False,
        'End Date': False,
        'Requires Virt-Who': False,
        'Consumed': False,
        'Entitlements': False
    }
    org = entities.Organization().create()
    _, temporary_local_manifest_path = mkstemp(prefix='manifest-', suffix='.zip')
    with manifests.clone() as manifest:
        with open(temporary_local_manifest_path, 'wb') as file_handler:
            file_handler.write(manifest.content.read())

    with session:
        session.organization.select(org.name)
        # Ignore "404 Not Found" as server will connect to upstream subscription service to verify
        # the consumer uuid, that will be displayed in flash error messages
        # Note: this happen only when using clone manifest.
        session.subscription.add_manifest(temporary_local_manifest_path,
                                          ignore_error_messages=['404 Not Found'])
        headers = session.subscription.filter_columns(checkbox_dict)
        assert headers[0] not in list(checkbox_dict)
        time.sleep(3)
        checkbox_dict.update((k, True) for k in checkbox_dict)
        col = session.subscription.filter_columns(checkbox_dict)
        assert set(col[1:]) == set(checkbox_dict)

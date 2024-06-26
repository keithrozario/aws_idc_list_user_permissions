import boto3
import botocore


def list_instances(client: boto3.client) -> list:
    """
    List all instances visible to this Principal
    """

    paginator = client.get_paginator("list_instances")
    instances = paginator.paginate().build_full_result()["Instances"]

    return instances


def list_accounts(client: boto3.client) -> dict:
    """
    List all accounts in the AWS Organization
    returns dictionary with AccountId as key
    """

    print(f"Looking up Accounts in your Organization...")

    paginator = client.get_paginator("list_accounts")
    accounts = paginator.paginate().build_full_result()["Accounts"]
    account_lookup = {item["Id"]: item for item in accounts}

    print(f"Total Accounts in Organization: {len(accounts)}")

    return account_lookup


def list_users(client: boto3.client, identity_store_id: str) -> list:
    """
    List all users in identity store (one Identity store per instance)
    """

    print(f"Looking up users in Identity store: {identity_store_id}")

    paginator = client.get_paginator("list_users")
    users = paginator.paginate(IdentityStoreId=identity_store_id).build_full_result()[
        "Users"
    ]

    user_lookup = {item["UserId"]: item for item in users}

    print(f"Total Users in Identity store {identity_store_id} : {len(users)}")

    return user_lookup


def list_groups(client: boto3.client, identity_store_id: str) -> list:
    """
    List all groups in identity store (one Identity store per instance)
    """
    paginator = client.get_paginator("list_groups")
    groups = paginator.paginate(IdentityStoreId=identity_store_id).build_full_result()[
        "Groups"
    ]
    return groups


def list_permission_sets(client: boto3.client, instance_arn: str) -> str:
    """
    List permission sets in the SSO instance
    """

    paginator = client.get_paginator("list_permission_sets")
    permission_sets = paginator.paginate(InstanceArn=instance_arn).build_full_result()[
        "PermissionSets"
    ]

    print(f"Total permission sets found in Organization: {len(permission_sets)}")

    return permission_sets


def list_user_assignments(
    client: boto3.client, user_id: str, instance_arn: str
) -> list:
    """
    List account assignments per user, this returns all permission sets by account for a user.
    """

    paginator = client.get_paginator("list_account_assignments_for_principal")
    user_assignments = paginator.paginate(
        InstanceArn=instance_arn, PrincipalId=user_id, PrincipalType="USER"
    ).build_full_result()["AccountAssignments"]
    # if user is provisioned via a GROUP, then the GroupId is returned as the PrincipalId
    # to maintain tracability, we add the 'OriginalPrincipalId' field which is always the user_id
    result = [
        dict(assignment, OriginalPrincipalId=user_id) for assignment in user_assignments
    ]

    return result

def list_managed_policy_permission_set(
    client: boto3.client, permission_set_arn: str, instance_arn: str
) -> list:
    """
    List managed policies of permission_set
    """

    paginator = client.get_paginator('list_managed_policies_in_permission_set')
    managed_policies = paginator.paginate(
        InstanceArn=instance_arn, PermissionSetArn=permission_set_arn
    ).build_full_result()["AttachedManagedPolicies"]

    return managed_policies


def describe_permissions_sets(
    client: boto3.client, permission_sets: list, instance_arn: str
) -> dict:
    """
    Returns lookup dictionary of permission sets
    Lookup dictionary has one key for each permission set, the key is the arn of the set.
    
    Each element of the lookup dictionary contains:
        Permission Set Description (e.g. Arn, CreatedAt) at the root 
        Permission Set Inline Policy, at 'inline_policy'
        Permission Set Permission Boundary at 'permission_boundary'
    """

    print(
        f"Looking up permission set details for {len(permission_sets)} permission sets"
    )

    permission_set_lookup = dict()
    for permission_set in permission_sets:
        permission_set_description = client.describe_permission_set(
            InstanceArn=instance_arn, PermissionSetArn=permission_set
        )["PermissionSet"]
        permission_set_lookup[permission_set] = permission_set_description
        
        permission_set_inline_policy = client.get_inline_policy_for_permission_set(
            InstanceArn=instance_arn, PermissionSetArn=permission_set
        )["InlinePolicy"]
        permission_set_lookup[permission_set]['inline_policy'] = permission_set_inline_policy

        try:
            permission_set_permission_boundary = client.get_permissions_boundary_for_permission_set(
                InstanceArn=instance_arn, PermissionSetArn=permission_set
            )["PermissionsBoundary"]
        except client.exceptions.ResourceNotFoundException:
            # No permission boundary found for this permission set
            permission_set_permission_boundary = False
        
        if not permission_set_permission_boundary:
            permission_set_lookup[permission_set]['permission_boundary'] = permission_set_permission_boundary


        managed_policies = list_managed_policy_permission_set(client, permission_set, instance_arn)
        permission_set_lookup[permission_set]['managed_policies '] = managed_policies
        
    return permission_set_lookup

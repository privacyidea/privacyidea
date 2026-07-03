/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { DestroyRef, inject, Signal, signal } from "@angular/core";
import {
  DetailFieldHandle,
  DetailsEditRegistry
} from "@components/shared/details-shared/field-editing/details-edit-registry.service";
import { EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";

export interface EditableFieldOptions {
  onOpen?: () => void;
  onCancel?: () => void;
  onCommit: () => boolean | void | Promise<boolean | void>;
}

export interface EditableField {
  readonly isEditing: Signal<boolean>;
  readonly editButtonsElement: EditableElement<unknown>;
  readonly toggle: () => void;
  readonly commit: () => void;
  readonly cancel: () => void;
}

export function injectEditableField(options: EditableFieldOptions): EditableField {
  const registry = inject(DetailsEditRegistry);
  const destroyRef = inject(DestroyRef);

  const isEditing = signal(false);

  const editButtonsElement: EditableElement<unknown> = {
    keyMap: { key: "" },
    isEditing,
    value: undefined
  };

  const commit = (): void => {
    const result = options.onCommit();
    if (result instanceof Promise) {
      // Keep edit mode open when the commit resolves to false (validation abort).
      void result.then((resolved) => {
        if (resolved !== false) {
          isEditing.set(false);
        }
      });
      return;
    }
    if (result !== false) {
      isEditing.set(false);
    }
  };

  const cancel = (): void => {
    options.onCancel?.();
    isEditing.set(false);
  };

  const toggle = (): void => {
    if (!isEditing()) {
      options.onOpen?.();
    }
    isEditing.update((editing) => !editing);
  };

  const handle: DetailFieldHandle = {
    isEditing,
    save: commit,
    cancel
  };

  registry.register(handle);
  destroyRef.onDestroy(() => registry.unregister(handle));

  return { isEditing, editButtonsElement, toggle, commit, cancel };
}
